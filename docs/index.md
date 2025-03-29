# Team IOSYS

[**Repository**](https://github.com/OSH-2025/IOSYS) | [**Course homepage**](https://osh-2025.github.io/)

Team IOSYS of USTC OSH 2025 - not "IOSYS".

## Our Team

Say hello to our awesome team.

<ClientOnly>
<VPTeamMembers size="small" :members="members" />
</ClientOnly>

## 项目进度

|      阶段       |    时间     |                             进展                             |                             分工                             |
| :-------------: | :---------: | :----------------------------------------------------------: | :---------------------------------------: |
| 选题 brainstorm | 02/24-03/06 | 各组员通过自行探索，都找到了一些感兴趣的方向；最终在统一讨论后确定以 nova（Javascript Engine）作为统一的方向。 |         各自成员在自己感兴趣的范围内自由展开主题调研         |
|    初步调研     | 03/07-03/21 | 对 nova 进行进一步调研，与开发者积极交流，学习 Javascript 相关语言特性与实现技术，尝试在其基础上进行开发。 | 熊桐睿与该项目负责者进行了充分交流，并提交了一些 contribution；其余组员进一步学习开发需要的技术基础。 |
|    初步调研     | 03/22-03/28 | nova 选题被老师否决，重新思考选题，并确定以 LLM+FS 为选题方向，以 AIOS、Graph RAG 等技术为实现思路。 | 冉竣宇负责了确定落实选题方向，并做了一定调研工作；熊桐睿、朱雨田在调研工作的基础上进一步调研了可行的实现方案；其他组员也参与了方案的讨论，提供了许多解决方案。 |
|  调研报告撰写   |    03/29    |    整理了 LLM+FS 方向的所有调研内容，撰写了一份调研报告。    | 朱雨田、冉竣宇负责了调研报告中大部分内容的编写。其余组员也参与了小部分内容的撰写。 |


<script setup>
import { VPTeamMembers } from 'vitepress/theme'

const members = randomize([
  {
    avatar: 'https://www.github.com/kermanx.png',
    name: '熊桐睿',
    // title: '',
    links: [
      { icon: 'github', link: 'https://github.com/kermanx' }
    ]
  },
  {
    avatar: 'https://www.github.com/HIJII-ZHANG.png',
    name: '张海川',
    // title: '',
    links: [
      { icon: 'github', link: 'https://github.com/HIJII-ZHANG' }
    ]
  },
  {
    avatar: 'https://www.github.com/rubatotree.png',
    name: '朱雨田',
​    // title: '',
​    links: [
​      { icon: 'github', link: 'https://github.com/rubatotree' }
​    ]
  },
  {
​    avatar: 'https://www.github.com/xuyifan7-star.png',
​    name: '许逸凡',
​    // title: '',
​    links: [
​      { icon: 'github', link: 'https://github.com/xuyifan7-star' }
​    ]
  },
  {
​    avatar: 'https://www.github.com/BloomFallr.png',
​    name: '冉竣宇',
​    // title: '',
​    links: [
​      { icon: 'github', link: 'https://github.com/BloomFallr' }
​    ]
  },
  {
​    avatar: 'https://www.github.com/chromiumarka.png',
​    name: '徐铭凯',
​    // title: '',
​    links: [
​      { icon: 'github', link: 'https://github.com/chromiumarka' }
​    ]
  },
])

function randomize(arr) {
  return arr.sort(() => Math.random() - 0.5)
}
</script>
