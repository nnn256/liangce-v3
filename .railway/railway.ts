import { defineRailway, github, project, service } from "railway/iac";

export default defineRailway(() => {
  const api = service("liangce-v3-api", {
    source: github("nnn256/liangce-v3", { branch: "main" }),
    build: { builder: "DOCKERFILE", dockerfilePath: "Dockerfile.hosted" },
    deploy: {
      numReplicas: 1,
      healthcheckPath: "/api/research/health",
      healthcheckTimeout: 120,
      sleepApplication: true,
      restartPolicyType: "ON_FAILURE",
      restartPolicyMaxRetries: 2,
      limitOverride: { containers: { cpu: 1, memoryBytes: 536870912 } },
    },
    env: { LIANGCE_HOSTING: "railway-free" },
  });
  return project("liangce-v3", { resources: [api] });
});
