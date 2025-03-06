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

Nova 是使用 Rust 编写的新的 JavaScript 引擎，目前尚未完成，通过了 55% 的 test262 测试。

根据 Nova 的[博客](https://trynova.dev/)，Nova 的主要创新在于：

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

### 来自 Nova 作者的回复

> 通过在 Nova 的 Discord 频道询问 Nova 的作者，[得到了热情的回复](https://discord.com/channels/1012084654389604372/1347207092477628537)。
>
> 个人认为以下内容更像 Nova 目前的代办事项，我们只需从中选取一些即可。
>
> （括号内是我关于这些事项的个人看法）

1. Helping me comb through all methods to make sure that no garbage collected values are used "use-after-free". I'm currently writing a step-by-step guide to explaining what this means, and this is mostly mechanical work that just needs to be done.

  校验和修复代码里是否有使用已经被垃圾回收的值的情况。（作者）会编写一个逐步的指南来解释这个问题。这个工作量不大，只需要机械地完成即可。（我们需要理解 Nova 里这个事情的含义，然后可以顺便做这个事情）

2. Taking up the dylint work that @eliassjogreen did the other day which enables writing custom lint rules, and using this to automatically check at least some of the above garbage collector use-after-free cases.

  编写 linter 规则来自动检查上面提到的垃圾回收器使用后释放的情况。（可能有点偏离我们的核心目标）

3. Implementing mostly straightforward `todo!()`s in builtin methods; there's still a good amount of these around Strings, some in Number and BigInt, and others.

  实现一些内置方法的 `todo!()`，目前还有很多。（从代码中找 `todo!()` 的调用，这个调用表示代码尚未写完，我们可以完成它们。）

4. Implementing class private properties: Not too bad on the tin, requires adding some new things which should be interesting.

  实现类的私有属性这个 JS 语法的支持。不算太难，可能需要添加一些新的东西。（或许是难度适中的选项）

5. Implementing Date: This is likely going to be somewhat arduous, but not terrible. You might be able to mostly finish this.

  实现 Date 对象（一个 JS 内置的对象）。（难度不大的选项）

6. Implementing Module and the ECMAScript Modules spec in general: This is a large body of work with lots of curious corners but still mostly sort-of-straightforward. Probably. You might be able to mostly finish this.

  实现模块。这个工作量很大，可能会有很多奇怪的 corner case，但还是比较直接的。（难度适中，但是确实挺麻烦的，但非常重要）

7. Implementing RegExp: This is going to be arduous, quite likely requiring a new bytecode and interpreter. You will not finish this, but you can probably make a decent dent into the work.

  实现正则表达式。这个工作量很大，可能需要新的字节码和解释器。你不可能完成这个工作，但可以做一些相关工作。（工作量挺大的喵，好在现在 oxc 已经支持把正则表达式解析成 AST 了，减少了一半的工作量）

8. Implementing a custom "Struct-of-Arrays" Vec for Nova (and oxc parser) to use: This would likely be a library outside of Nova proper as we'll probably want to share this with oxc, and goes to a "lower level" as it's not within the engine but something that the engine would use. This would go pretty deep indeed but isn't a large body of work on the tin. Complexity comes from getting it correct 🙂

  实现一个自定义的 "Struct-of-Arrays" Vec 来供 Nova 和 oxc 使用。这可能是一个独立于 Nova 的库，因为我们可能希望与 oxc 共享这个库。这个工作量不大，但复杂性在于要正确地实现它。（需要对这个概念有非常深刻的理解）

9. Parallelising Nova's garbage collector's tracing algorithm. It's currently built with the idea of eventually being parallel but it's not actually parallelised. Maybe not enough on its own to fill the time.

  将 Nova 的垃圾回收器的 tracing 算法并行化。它目前是以将来并行化为目标编写的，但实际上并没有并行化。单独做这件事可能不够用完时间。（难啊，也许可以尝试）

10. Implementing ephemerons in Nova's GC. This... is not difficult on the tin, but the devil is in the details. Ephemerons are difficult to do efficiently, and efficiency is what we'd want with these so this might offer endless opportunity for polishing 🙂

  实现 ephemerons（GC 相关的一个概念，[参考](https://blog.codingnow.com/2018/10/lua_gc.html)）。这件事本身不难，但细节上可能会很复杂。ephemerons 很难高效地实现，而我们希望它是高效的，所以这可能会提供无尽的打磨机会。（难啊，也许可以尝试）

11. Making Nova's garbage collector's tracing (and maybe one step of the sweeping) concurrent. This is a huge amount of work, will drive you insane, and you won't finish in time.

  将 Nova 的垃圾回收器的 tracing（和 sweeping 的一个步骤）并行化。这是一个巨大的工作量，会让你发疯，你不可能在规定时间内完成。（太难了）

12. Refactor Nova's bytecode interpreter to use a single stack (it's currently a sort of segmented stacks system). Fighting with the borrow checker inbound.

  重构 Nova 的字节码解释器，使用单个栈（目前是一个分段栈的系统）。这可能会和 Rust 的 borrow checker 发生冲突。（困难，也许可以尝试）

13. Refactor / try out the interpreter as register based instead of stack based. This is a huge amount of work, touches nearly everything in the bytecode generation, and will drive you insane.

  重构或尝试将解释器改为基于寄存器而非栈的实现。这是一个巨大的工作量，几乎涉及字节码生成中的所有内容，会让你发疯。（太难了，但或许我们可以部分做到）

14. `#![no_std]` support: This requires quite a bit of work but isn't particularly impossible.

  实现 `#![no_std]` 的支持。这需要一些工作，但并不是不可能。（也许可以尝试）

15. Implement Object shapes: Not too hard, very useful in the long run. Best combined with:

  实现 Object shapes（一个优化方法，已被各个引擎广泛使用）。这并不难，从长远来看非常有用。最好和下面的 inline caching 一起做。（感觉是非常好的选项，有难度但我们有很多可以参考的实现）

16. Implement inline caching: This is The Single Best performance optimisation that a JavaScript engine has (or so I'm told). That being said, I've never done this so this'll be a learning opportunity for all of us.

  实现 inline caching。这是我听说过的 JavaScript 引擎中最好的性能优化。不过，我从来没有做过，所以这对我们所有人来说都是一个学习的机会。（感觉也是不错的选项）

17. Implement the Temporal proposal. Technically, this might not be too hard as there exist rust libraries that explicitly model themselves after this proposal's API. You can probably mostly just wrap a library like that and it'll get you pretty far. But the API surface is large so this will still be a lot of work.

  实现 Temporal 提案。技术上来说，这可能并不难，因为有一些 Rust 库明确地以这个提案的 API 为模型。你可以将这样的库包装起来，这样就能走得很远。但由于 API 很多，所以这仍然会是一个巨大的工作量。（和上文的 5. Date 类似但肯定更加复杂些）
