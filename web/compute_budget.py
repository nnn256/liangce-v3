"""One shared allocation budget for research, previews and replay workers."""
from collections import OrderedDict
from contextlib import contextmanager
from functools import wraps
import ctypes,gc,os,threading,time
from fastapi import HTTPException

_gate=threading.Lock();_local=threading.local();_state_guard=threading.Lock()
_state={'active':None,'started':None,'rejected':0}


def release_memory():
    gc.collect()
    if os.name=='posix':
        try:ctypes.CDLL(None).malloc_trim(0)
        except (AttributeError,OSError):pass


def status():
    with _state_guard:return {**_state,'concurrency_limit':1}


@contextmanager
def budget(label,*,wait=False):
    if getattr(_local,'depth',0):
        _local.depth+=1
        try:yield
        finally:_local.depth-=1
        return
    if not _gate.acquire(timeout=120 if wait else .1):
        with _state_guard:_state['rejected']+=1
        raise HTTPException(429,'结构计算正在处理其他请求，请稍后自动重试',headers={'Retry-After':'10'})
    _local.depth=1
    with _state_guard:_state.update(active=label,started=time.monotonic())
    try:yield
    finally:
        _local.depth=0
        with _state_guard:_state.update(active=None,started=None)
        release_memory();_gate.release()


def bounded(label,*,wait=False):
    def decorate(function):
        @wraps(function)
        def call(*args,**kwargs):
            with budget(label,wait=wait):return function(*args,**kwargs)
        return call
    return decorate


class ByteCache:
    """Hold only compressed immutable payloads, evicting before insertion."""
    def __init__(self,max_bytes=8*1024*1024,max_entries=2):
        self.max_bytes=max_bytes;self.max_entries=max_entries;self.bytes=0;self.items=OrderedDict();self.lock=threading.RLock()
    def clear(self):
        with self.lock:self.items.clear();self.bytes=0
    def get(self,key):
        with self.lock:
            if key not in self.items:return None
            self.items.move_to_end(key);return self.items[key]
    def put(self,key,value):
        if not isinstance(value,bytes):raise TypeError('Cache accepts immutable bytes only')
        with self.lock:
            previous=self.items.pop(key,None)
            if previous is not None:self.bytes-=len(previous)
            if len(value)>self.max_bytes:return
            while self.items and (self.bytes+len(value)>self.max_bytes or len(self.items)>=self.max_entries):
                _,old=self.items.popitem(last=False);self.bytes-=len(old)
            self.items[key]=value;self.bytes+=len(value)
