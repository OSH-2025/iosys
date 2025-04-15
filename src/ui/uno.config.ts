import { defineConfig, presetAttributify, presetIcons, presetWind3, transformerDirectives } from "unocss";

export default defineConfig({
  presets: [
    presetAttributify(),
    presetWind3(),
    presetIcons(),
  ],
  transformers: [
    transformerDirectives(),
  ],
});
