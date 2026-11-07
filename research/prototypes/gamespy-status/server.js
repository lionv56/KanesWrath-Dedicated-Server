"use strict";

const net = require("node:net");

const TERMINATOR = Buffer.from("\\final\\", "ascii");
const MAX_BUFFER = 65536;

class GameSpyFrameParser {
  constructor(onMessage) {
    this.buffer = Buffer.alloc(0);
    this.onMessage = onMessage;
  }

  push(chunk) {
    if (!Buffer.isBuffer(chunk)) {
      throw new TypeError("Expected Buffer");
    }

    this.buffer = Buffer.concat([this.buffer, chunk]);

    let index;

    while ((index = this.buffer.indexOf(TERMINATOR)) !== -1) {
      const end = index + TERMINATOR.length;
      const message = this.buffer.subarray(0, end);

      this.buffer = this.buffer.subarray(end);

      if (message.length > MAX_BUFFER) {
        throw new Error("Message exceeds size limit");
      }

      this.onMessage(message);
    }

    if (this.buffer.length > MAX_BUFFER) {
      throw new Error("Incomplete message exceeds size limit");
    }
  }
}

function createGameSpyServer(options = {}) {
  const host = options.host || "127.0.0.1";
  const port = options.port === undefined ? 29900 : options.port;
  const onMessage = options.onMessage || (() => {});

  const server = net.createServer((socket) => {
    let messageCount = 0;

    const parser = new GameSpyFrameParser((message) => {
      messageCount++;

      // Geen ruwe payload of eventuele credentials loggen.
      onMessage({
        bytes: message.length,
        messageNumber: messageCount
      });
    });

    socket.on("data", (chunk) => {
      try {
        parser.push(chunk);
      } catch (error) {
        console.error("[REJECTED]", error.message);
        socket.destroy();
      }
    });

    socket.on("error", (error) => {
      console.error("[SOCKET]", error.code || error.message);
    });
  });

  return {
    server,
    start() {
      return new Promise((resolve, reject) => {
        server.once("error", reject);

        server.listen(port, host, () => {
          server.removeListener("error", reject);
          resolve(server.address());
        });
      });
    },
    stop() {
      return new Promise((resolve, reject) => {
        server.close((error) => {
          if (error) reject(error);
          else resolve();
        });
        server.closeAllConnections?.();
      });
    }
  };
}

module.exports = {
  GameSpyFrameParser,
  createGameSpyServer
};

if (require.main === module) {
  const app = createGameSpyServer({
    onMessage: (info) => {
      console.log(
        "[MESSAGE]",
        "number=" + info.messageNumber,
        "bytes=" + info.bytes
      );
    }
  });

  app.start()
    .then((address) => {
      console.log(
        "[LISTENING]",
        address.address + ":" + address.port
      );
      console.log(
        "Prototype only. No authentication or lobby implemented."
      );
    })
    .catch((error) => {
      console.error("[FAIL]", error.message);
      process.exitCode = 1;
    });
}