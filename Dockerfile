# Self-host anywhere: Render / Railway / Fly / a VPS / Docker.
# The app is a dependency-free Node static host (sta1610/server.js).
FROM node:20-alpine

WORKDIR /app
ENV NODE_ENV=production PORT=8080 HOST=0.0.0.0

COPY package.json ./
COPY sta1610/ ./sta1610/

EXPOSE 8080
USER node
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD node -e "fetch('http://127.0.0.1:'+(process.env.PORT||8080)+'/healthz').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "sta1610/server.js"]
