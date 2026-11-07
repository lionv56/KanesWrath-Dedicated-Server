"use strict";

const assert = require("node:assert/strict");
const net = require("node:net");

async function main() {
  const url = "http://127.0.0.1:8080/health";
  const initialResponse = await fetch(url);
  assert.equal(initialResponse.status, 200);

  const initial = await initialResponse.json();
  assert.equal(initial.status, "ok");
  assert.equal(initial.realClientCompatible, false);

  const socket = net.createConnection({
    host: "127.0.0.1",
    port: 29901
  });

  await new Promise((resolve, reject) => {
    socket.once("connect", resolve);
    socket.once("error", reject);
  });

  socket.write("\\status\\");
  socket.write("\\final\\");
  socket.end();

  let success = false;

  for (let i = 0; i < 30; i++) {
    const response = await fetch(url);
    assert.equal(response.status, 200);
    const result = await response.json();

    if (result.receivedFrames >= initial.receivedFrames + 1) {
      success = true;
      break;
    }

    await new Promise((resolve) => setTimeout(resolve, 100));
  }

  assert.equal(success, true);

  console.log("[PASS] HTTP health");
  console.log("[PASS] Real Docker TCP connection");
  console.log("[PASS] Synthetic frame processed");
  console.log("[RESULT] CONTAINER_GATEWAY_ACCEPTED_LOCALLY");
  console.log("[RESULT] REAL_GAME_COMPATIBILITY_NOT_TESTED");
}

main().catch((err) => {
  console.error("[FAIL]", err.message);
  process.exitCode = 1;
});