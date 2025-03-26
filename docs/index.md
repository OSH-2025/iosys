# Team IOSYS

[**Repository**](https://github.com/OSH-2025/IOSYS) | [**Course homepage**](https://osh-2025.github.io/)

Team IOSYS of USTC OSH 2025 - not "IOSYS".

## Our Team

Say hello to our awesome team.

<ClientOnly>
<VPTeamMembers size="small" :members="members" />
</ClientOnly>

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
    // title: '',
    links: [
      { icon: 'github', link: 'https://github.com/rubatotree' }
    ]
  },
  {
    avatar: 'https://www.github.com/xuyifan7-star.png',
    name: '许逸凡',
    // title: '',
    links: [
      { icon: 'github', link: 'https://github.com/xuyifan7-star' }
    ]
  },
  {
    avatar: 'https://www.github.com/BloomFallr.png',
    name: '冉竣宇',
    // title: '',
    links: [
      { icon: 'github', link: 'https://github.com/BloomFallr' }
    ]
  },
  {
    avatar: 'https://www.github.com/chromiumarka.png',
    name: '徐铭凯',
    // title: '',
    links: [
      { icon: 'github', link: 'https://github.com/chromiumarka' }
    ]
  },
])

function randomize(arr) {
  return arr.sort(() => Math.random() - 0.5)
}
</script>
