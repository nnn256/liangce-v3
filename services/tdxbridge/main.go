// Loopback bridge for the documented oficcejo/tdx-api full-history contract.
// Upstream pinned in Dockerfile.hosted; protocol implementation: injoyai/tdx.
package main

import (
	"encoding/json"
	"fmt"
	"github.com/injoyai/tdx"
	"log"
	"net/http"
	"os"
	"regexp"
	"strings"
	"sync"
	"time"
)

var mutex sync.Mutex
var connection *tdx.Client
var idleTimer *time.Timer
var validCode = regexp.MustCompile(`^(sh6[0-9]{5}|sz(0[0-9]{5}|30[0-9]{4})|bj[0-9]{6})$`)
var kinds = map[string]uint8{"minute1": 7, "minute5": 0, "minute15": 1, "minute30": 2, "hour": 3, "day": 9, "week": 5, "month": 6, "quarter": 10, "year": 11}

func response(w http.ResponseWriter, data any, err error) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("Cache-Control", "no-store")
	code, message := 0, "success"
	if err != nil {
		code, message = -1, err.Error()
	}
	json.NewEncoder(w).Encode(map[string]any{"code": code, "message": message, "data": data})
}

func client() (*tdx.Client, error) {
	if connection != nil {
		return connection, nil
	}
	// Hosts are the same public protocol endpoints used by the supplied service.
	c, err := tdx.DialHostsRange(tdx.Hosts, tdx.WithDebug(false), tdx.WithLevel(tdx.LevelError), tdx.WithRedial(false))
	if err != nil {
		return nil, err
	}
	c.SetTimeout(8 * time.Second)
	connection = c
	return c, nil
}

func releaseIdle() {
	if idleTimer != nil {
		idleTimer.Stop()
	}
	idleTimer = time.AfterFunc(45*time.Second, func() {
		mutex.Lock()
		defer mutex.Unlock()
		if connection != nil {
			connection.Close()
			connection = nil
		}
	})
}

func history(w http.ResponseWriter, r *http.Request) {
	code := strings.ToLower(r.URL.Query().Get("code"))
	kind := r.URL.Query().Get("type")
	category, ok := kinds[kind]
	if !validCode.MatchString(code) || !ok {
		response(w, nil, fmt.Errorf("valid exchange-prefixed stock and exact period required"))
		return
	}
	mutex.Lock()
	defer mutex.Unlock()
	defer releaseIdle()
	c, err := client()
	if err != nil {
		response(w, nil, err)
		return
	}
	result, err := c.GetKlineAll(category, code)
	if err != nil {
		c.Close()
		connection = nil
		response(w, nil, err)
		return
	}
	response(w, map[string]any{"count": len(result.List), "list": result.List, "meta": map[string]any{
		"source": "tdx", "type": kind, "adjustment": "unadjusted", "batch_limit": 800,
		"coverage": "all returned native pages; source retention may be finite",
		"upstream": "oficcejo/tdx-api@ea07dccb67aeb92ebde851ac31503b4bf457a318"}}, nil)
}

func quotes(w http.ResponseWriter, r *http.Request) {
	var input struct {
		Codes []string `json:"codes"`
	}
	if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 8192)).Decode(&input); err != nil {
		response(w, nil, err)
		return
	}
	if len(input.Codes) < 1 || len(input.Codes) > 50 {
		response(w, nil, fmt.Errorf("batch must have1..50 codes"))
		return
	}
	for _, code := range input.Codes {
		if !validCode.MatchString(code) {
			response(w, nil, fmt.Errorf("explicit market code required"))
			return
		}
	}
	mutex.Lock()
	defer mutex.Unlock()
	defer releaseIdle()
	c, err := client()
	if err != nil {
		response(w, nil, err)
		return
	}
	result, err := c.GetQuote(input.Codes...)
	if err != nil {
		c.Close()
		connection = nil
	}
	response(w, result, err)
}

func main() {
	port := os.Getenv("LIANGCE_TDX_PORT")
	if port == "" {
		port = "18081"
	}
	if !regexp.MustCompile(`^[0-9]{4,5}$`).MatchString(port) {
		log.Fatal("invalid loopback port")
	}
	http.HandleFunc("/api/health", func(w http.ResponseWriter, r *http.Request) {
		response(w, map[string]any{"status": "ok", "provider": "tdx"}, nil)
	})
	http.HandleFunc("/api/kline-all/tdx", history)
	http.HandleFunc("/api/batch-quote", quotes)
	log.Printf("TDX loopback bridge on127.0.0.1:%s", port)
	server := http.Server{Addr: "127.0.0.1:" + port, ReadHeaderTimeout: 5 * time.Second, WriteTimeout: 100 * time.Second}
	log.Fatal(server.ListenAndServe())
}
