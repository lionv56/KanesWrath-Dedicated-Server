FROM node:24-alpine

ENV NODE_ENV=production
WORKDIR /app

COPY --chown=node:node package.json server.js ./

USER node

EXPOSE 29900 8080

CMD ["node", "server.js"]