import "dotenv/config";
import { defineConfig } from "@hey-api/openapi-ts";

if (!process.env.API_URL) {
  throw new Error("Please define API_URL in your .env");
}

export default defineConfig({
  input: `${process.env.API_URL}/openapi.json`,
  output: "src/client",
});
