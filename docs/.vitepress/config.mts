// import { withMermaid } from "vitepress-plugin-mermaid";
import { defineConfig } from "vitepress";
import Footnote from 'markdown-it-footnote'
import { globSync } from "tinyglobby";
import { basename } from "path";
import UnoCSS from 'unocss/vite'
import { presetIcons, presetWind3, presetAttributify, transformerDirectives } from 'unocss';

export default defineConfig({
  title: "Team IOSYS",
  description: "Team IOSYS of USTC OSH 2025",
  themeConfig: {
    siteTitle: "Team IOSYS",
    sidebar: [
      {
        text: "Home",
        link: "/",
      },
      {
        text: "Schedule",
        link: "/schedule",
      },
      {
        text: "Notes",
        items: globSync("notes/*.md").map((path) => {
          const name = basename(path, ".md");
          const id = name.match(/^(\d+)\-/)?.[1];
          if (!id) {
            console.log(`Invalid note name: ${name}. Should start with an ID`);
          }
          let displayName = id ? name.slice(id.length + 1) : name;
          displayName = displayName.split('-').map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
          return { id: +(id ?? ''), text: displayName, link: `/notes/${name}` };
        }).sort((a, b) => a.id - b.id),
      },
      {
        text: "调研报告",
        items: globSync("preliminary/*.md").map((path) => {
          const name = basename(path, ".md");
          return { text: name, link: `/preliminary/${name}` };
        }),
      },
    ],
  },
  vite: {
    plugins: [
      UnoCSS({
        presets: [
          presetWind3(),
          presetAttributify(),
          presetIcons(),
        ],
        transformers: [
          transformerDirectives(),
        ],
      }),
    ],
  },
  markdown: {
    theme: "dark-plus",
    math: true,
    config(md) {
      md.use(Footnote);
    },
  },
  appearance: "force-dark",
  head: [
    [
      "link",
      {
        rel: "icon",
        href: "/favicon.ico",
      },
    ],
  ],
});
