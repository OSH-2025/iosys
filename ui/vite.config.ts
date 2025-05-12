import { defineConfig } from "vite";
import Vue from "@vitejs/plugin-vue";
import UnoCss from "unocss/vite";

export default defineConfig({
  plugins: [Vue(), UnoCss()],
  envDir: '../',
});
