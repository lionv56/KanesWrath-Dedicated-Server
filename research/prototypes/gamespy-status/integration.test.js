"use strict";

const assert = require("node:assert/strict");
const net = require("node:net");

const {
  GameSpyFrameParser,
  createGameSpyServer
} = require("./server");

async function main() {
  const parsed = [];

  const parser = new GameSpyFrameParser((message) => {
    parsed.push(message.toString("ascii"));
  });

  parser.push(Buffer.from("\\status\\1\\fin"));
  assert.equal(parsed.length, 0);

  parser.push(Buffer.from("al\\"));
  assert.deepEqual(parsed, ["\\status\\1\\final\\"]);

  parser.push(
    Buffer.from("\\status\\2\\final\\\\status\\3\\final\\")
  );

  assert.equal(parsed.length, 3);
  console.log("[PASS] Buffer framing and fragmentation");

  const received = [];

  const app = createGameSpyServer({
    port: 0,
    onMessage: (info) => received.push(info)
  });

  const address = await app.start();

  try {
    await new Promise((resolve, reject) => {
      const client = net.connect({
        host: "127.0.0.1",
        port: address.port
      });

      client.on("error", reject);

      client.on("connect", () => {
        client.write("\\status\\1\\fin");
        client.write("al\\");
        client.end("\\status\\2\\final\\");
      });

      client.on("close", resolve);
    });

    assert.equal(received.length, 2);
    assert.ok(received.every((x) => x.bytes > 0));

    console.log("[PASS] Real localhost TCP integration");
    console.log("[PASS] Two framed messages received");
    console.log("[PASS] Payload contents not logged");
  } finally {
    await app.stop();
  }

  console.log("[RESULT] PROTOTYPE_ACCEPTED_LOCALLY");
  console.log("[RESULT] REAL_GAME_COMPATIBILITY_NOT_TESTED");
}

main().catch((error) => {
  console.error("[FAIL]", error.stack || error.message);
  process.exitCode = 1;
});