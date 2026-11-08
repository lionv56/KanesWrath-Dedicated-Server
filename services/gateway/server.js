"use strict";

const net = require("node:net");
const http = require("node:http");
const { createFeslProbe } = require("./fesl-probe");

const HOST = "0.0.0.0";
const TCP_PORT = 29900;
const HTTP_PORT = 8080;
const DELIMITER = Buffer.from("\\final\\", "ascii");
const MAX_BUFFER = 65536;

let activeConnections = 0;
let receivedFrames = 0;

const tcp = net.createServer((socket) => {
  activeConnections++;
  let pending = Buffer.alloc(0);

  socket.setTimeout(30000, () => socket.destroy());

  socket.on("data", (chunk) => {
    pending = Buffer.concat([pending, chunk]);

    while (true) {
      const position = pending.indexOf(DELIMITER);
      if (position === -1) break;

      const frameEnd = position + DELIMITER.length;

      if (frameEnd > MAX_BUFFER) {
        socket.destroy();
        return;
      }

      receivedFrames++;
      pending = pending.subarray(frameEnd);
    }

    if (pending.length > MAX_BUFFER) {
      socket.destroy();
    }
  });

  socket.on("error", () => {});
  socket.on("close", () => {
    activeConnections--;
  });
});

const web = http.createServer((req, res) => {
  if (req.method !== "GET" || req.url !== "/health") {
    res.writeHead(404).end();
    return;
  }

  res.writeHead(200, {
    "Content-Type": "application/json",
    "Cache-Control": "no-store"
  });

  res.end(JSON.stringify({
    status: "ok",
    service: "kwds-gateway",
    experimental: true,
    realClientCompatible: false,
    activeConnections,
    receivedFrames,
    feslProbe: feslProbe.stats()
  }));
});

tcp.on("error", (error) => {
  console.error("TCP listener failed:", error.code);
  process.exitCode = 1;
});

web.on("error", (error) => {
  console.error("Health listener failed:", error.code);
  process.exitCode = 1;
});

const feslProbe = createFeslProbe();
feslProbe.listen(18840, HOST);
tcp.listen(TCP_PORT, HOST);
web.listen(HTTP_PORT, HOST);

function shutdown() {
  tcp.close();
  feslProbe.close();
  web.close();
}

process.on("SIGTERM", shutdown);
process.on("SIGINT", shutdown);