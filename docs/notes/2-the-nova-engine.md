# The Nova Engine

> Author: 熊桐睿

关于 The Nova JavaScript Engine，作为备选的选题之一。

## 背景

目前已知的可用的 JavaScript 引擎有：

| 名称           | 语言 | 说明                        |
| -------------- | ---- | --------------------------- |
| V8             | C++  | 用于 Chrome 和 Node.js      |
| JavaScriptCore | C++  | 用于 Safari 和 Bun          |
| SpiderMonkey   | C++  | 用于 Firefox                |
| LibJS          | C++  | 用于 Ladybird 浏览器        |
| QuickJS        | C    | 简单轻量。核心源码 5.5 万行 |
| Hermes         | C++  | 用于 React Native           |
| NJS            | C    | JS 子集，用于 nginx         |

这些引擎都使用 C/C++ 编写。

## About Nova

Nova 是使用 Rust 编写的新的 JavaScript 引擎，目前尚未完成。

根据它的[博客](https://trynova.dev/)，Nova 的主要创新在于：

- Data-oriented Design（思想：CPU 读取内存的单位是 cache line，而计算本身比内存访问快得多，因此要尽可能高效地使用 cache line）
  - 尽可能地将可能在访问时间上接近的数据放在一起
  - 尽可能地减少对象的大小，将一般用不到的字段移动到外部哈希表
- 使用 index 而非指针来表示对象的引用，保证访问的安全性且足够高效
- 通过 Rust 的所有权和借用系统来保证垃圾回收的安全性

总之就是更快（Data-oriented Design）、更安全（Rust）。

目前 Nova 没有 JIT 编译器。JS 代码先编译到字节码，然后在 Nova 虚拟机中解释运行。由于目前的人手和开发时间的客观条件，性能上比肩有 JIT 的 V8 几乎是不可能的；但如果能证明这个方向能走通，后续社区就可以加大投入，达到甚至超过 V8 的性能。

## 我们可以做什么

首先，由于 Nova 并非简单地从 C 到Rust 的改写，而是采用了许多新的设计，Nova 的作者和贡献者们也仍在不断地进行新的探索和尝试，因此我认为在一个学期内直接将 Nova 完成是不现实的。

但我们依然有许多可以做的事情：

1. 实现剩余的 JavaScript 内置对象（[对应的 milestone](https://github.com/trynova/nova/milestone/1)）。掌握 Nova 的原理之后，对照 ECMA262 规范，直接编写即可，应该不会很难。

2. 博客中提到，Nova 目前没有使用 Rust 的 lifetimes 来保证垃圾回收的安全性（写了又删了，目前正在重新添加回去），我们可以作出一些尝试。

... 未完待续
