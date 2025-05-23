const express = require("express");
const http = require("http");

const TARGET = "https://178.71.232.174:5173";

const app = express();

app.use((req, res) => {
  // Preserve path and query string
  const url = `${TARGET}${req.originalUrl}`;
  res.redirect(301, url);
});

// Start HTTP server on port 80
http.createServer(app).listen(80, () => {
  console.log("HTTP redirect server running on port 80");
});
