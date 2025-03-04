// import { withMermaid } from "vitepress-plugin-mermaid";
import { defineConfig } from "vitepress";
import { globSync } from "tinyglobby";
import { basename } from "path";

export default defineConfig({
  title: "OSH Project",
  description: "",
  themeConfig: {
    siteTitle: "OSH Project",
    sidebar: [
      {
        text: "Home",
        link: "/",
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
    ],
  },
  vite: {
    plugins: [
    ],
  },
  markdown: {
    theme: "dark-plus",
    math: true,
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
