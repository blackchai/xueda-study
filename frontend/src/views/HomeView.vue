<script setup lang="ts">
import {
  ArrowRight,
  Calendar,
  Check,
  Flag,
  Medal,
  Right,
  Timer,
  UserFilled,
} from '@element-plus/icons-vue'
import { ref } from 'vue'

import BrandLogo from '@/components/BrandLogo.vue'

const mobileNavOpen = ref(false)

const features = [
  {
    icon: Flag,
    tone: 'violet',
    number: '01',
    title: '把大目标，拆成今天能完成的事',
    description: '建立阶段目标、拆解学习任务、跟踪真实完成度，让计划不再停在清单里。',
    points: ['目标与任务联动', '进度清晰可追踪'],
  },
  {
    icon: Calendar,
    tone: 'cyan',
    number: '02',
    title: '每一次专注，都留下看得见的积累',
    description: '用日历记录时长、内容与状态，在连续打卡和趋势反馈中建立稳定节奏。',
    points: ['每日学习复盘', '周趋势与连续天数'],
  },
  {
    icon: UserFilled,
    tone: 'orange',
    number: '03',
    title: '找到真正合拍的学习搭子',
    description: '综合目标、时间、方式和阶段计算匹配分，并解释推荐原因，不只看兴趣标签。',
    points: ['四维可解释匹配', '邀请与双向确认'],
  },
  {
    icon: Medal,
    tone: 'green',
    number: '04',
    title: '在小组里，让坚持变成共同节奏',
    description: '加入主题学习小组，通过共同任务、成员动态和周榜获得温和的同伴推动。',
    points: ['主题共学空间', '打卡排行榜'],
  },
]
</script>

<template>
  <div class="landing-page">
    <header class="landing-nav">
      <BrandLogo />
      <nav class="landing-nav__links" aria-label="首页导航">
        <a href="#features">核心功能</a>
        <a href="#journey">如何开始</a>
        <a href="#matching">智能匹配</a>
      </nav>
      <div class="landing-nav__actions">
        <RouterLink class="login-link" to="/auth">登录</RouterLink>
        <RouterLink class="nav-cta" to="/auth?mode=register">免费开始 <ArrowRight /></RouterLink>
      </div>
      <button class="mobile-menu-button" type="button" aria-label="切换首页导航" @click="mobileNavOpen = !mobileNavOpen">
        <span></span><span></span><span></span>
      </button>
      <nav v-if="mobileNavOpen" class="mobile-nav-panel" aria-label="移动端首页导航">
        <a href="#features" @click="mobileNavOpen = false">核心功能</a>
        <a href="#journey" @click="mobileNavOpen = false">如何开始</a>
        <a href="#matching" @click="mobileNavOpen = false">智能匹配</a>
        <RouterLink to="/auth">登录 / 注册</RouterLink>
      </nav>
    </header>

    <main id="main-content" tabindex="-1">
      <section class="hero-section">
        <div class="hero-orb hero-orb--one"></div>
        <div class="hero-orb hero-orb--two"></div>
        <div class="hero-copy">
          <span class="hero-badge"><span>✦</span> 为认真学习的人，找到同行者</span>
          <h1>让自律不再孤单<br /><em>让学习有人同行</em></h1>
          <p>从目标规划、每日打卡，到学习搭子与共学小组。学搭把一个人的坚持，变成彼此看得见的成长。</p>
          <div class="hero-actions">
            <RouterLink class="primary-cta" to="/auth?mode=register">
              开始我的学习计划 <ArrowRight />
            </RouterLink>
            <RouterLink class="secondary-cta" to="/dashboard">
              查看交互原型 <Right />
            </RouterLink>
          </div>
          <div class="hero-assurances" aria-label="产品说明">
            <span><Check /> 第一阶段免费体验</span>
            <span><Check /> 数据仅存本机</span>
            <span><Check /> 无收费 AI 接口</span>
          </div>
        </div>

        <div class="hero-visual" aria-label="学习工作台界面预览">
          <div class="preview-window">
            <div class="preview-window__bar">
              <span></span><span></span><span></span>
              <small>今天也向目标靠近一点</small>
            </div>
            <div class="preview-layout">
              <aside class="preview-sidebar">
                <span class="preview-mark">学</span>
                <i class="is-active"></i><i></i><i></i><i></i><i></i>
              </aside>
              <div class="preview-main">
                <div class="preview-greeting">
                  <div><small>11 月 · 星期三</small><strong>晚上好，林小满 👋</strong></div>
                  <span>连续 11 天</span>
                </div>
                <div class="preview-stats">
                  <div><small>今日任务</small><strong>1 / 3</strong></div>
                  <div><small>本周专注</small><strong>12.6h</strong></div>
                  <div><small>目标进度</small><strong>54%</strong></div>
                </div>
                <div class="preview-content">
                  <div class="preview-tasks">
                    <div class="preview-card-title"><strong>今日任务</strong><span>查看全部</span></div>
                    <label class="done"><span>✓</span><i><b>高数错题复盘</b><small>60 分钟 · 考研计划</small></i></label>
                    <label><span></span><i><b>数据结构：树与二叉树</b><small>90 分钟 · 考研计划</small></i></label>
                    <label><span></span><i><b>英语阅读精读 2 篇</b><small>45 分钟 · 考研计划</small></i></label>
                  </div>
                  <div class="preview-focus">
                    <small>本周学习目标</small>
                    <div class="mini-ring"><span>72%</span></div>
                    <strong>还差 4.2 小时</strong>
                    <p>保持现在的节奏</p>
                  </div>
                </div>
                <div class="preview-bars">
                  <div v-for="(height, index) in [42, 68, 55, 82, 64, 90, 36]" :key="index">
                    <span :style="{ height: `${height}%` }"></span>
                    <small>{{ ['一', '二', '三', '四', '五', '六', '日'][index] }}</small>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="floating-match-card">
            <span class="avatar">陈</span>
            <div><small>今日推荐搭子</small><strong>陈知行</strong><em>目标相近 · 晚间重合</em></div>
            <b>92<small>分</small></b>
          </div>
          <div class="floating-check-card"><span>✓</span><div><strong>打卡成功</strong><small>连续学习 11 天</small></div></div>
        </div>
      </section>

      <section id="features" class="features-section content-section">
        <div class="section-intro">
          <span>学习闭环</span>
          <h2>从“想要坚持”，到“真的在进步”</h2>
          <p>每个功能都围绕真实学习过程设计，不制造焦虑，只帮助你把注意力放回下一步行动。</p>
        </div>
        <div class="feature-grid">
          <article v-for="feature in features" :key="feature.title" class="feature-card">
            <span class="feature-number">{{ feature.number }}</span>
            <span class="feature-icon" :class="`tone-${feature.tone}`"><component :is="feature.icon" /></span>
            <h3>{{ feature.title }}</h3>
            <p>{{ feature.description }}</p>
            <ul>
              <li v-for="point in feature.points" :key="point"><Check /> {{ point }}</li>
            </ul>
          </article>
        </div>
      </section>

      <section id="journey" class="journey-section content-section">
        <div class="journey-copy">
          <span class="section-kicker">开始很简单</span>
          <h2>三步建立你的共学节奏</h2>
          <p>先说清自己要去哪里，再记录每一天的真实投入，最后找到时间和方式都合拍的人。</p>
          <RouterLink class="inline-link" to="/auth?mode=register">创建学习档案 <ArrowRight /></RouterLink>
        </div>
        <ol class="journey-list">
          <li>
            <span>01</span>
            <div><strong>设定目标与可用时段</strong><p>选择学习方向、阶段和每周时间，让计划足够具体。</p></div>
            <Flag />
          </li>
          <li>
            <span>02</span>
            <div><strong>完成任务并留下打卡</strong><p>记录时长和学习内容，让进步有迹可循。</p></div>
            <Timer />
          </li>
          <li>
            <span>03</span>
            <div><strong>连接搭子或加入小组</strong><p>用共同节奏互相提醒，在小组中获得持续反馈。</p></div>
            <UserFilled />
          </li>
        </ol>
      </section>

      <section id="matching" class="matching-section content-section">
        <div class="matching-visual">
          <div class="match-rings"><span></span><span></span><span></span></div>
          <div class="match-person match-person--me"><span>林</span><strong>我的学习档案</strong><small>考研 · 晚间 · 强化</small></div>
          <div class="match-line"><i></i><b>92%</b><i></i></div>
          <div class="match-person match-person--buddy"><span>陈</span><strong>推荐搭子</strong><small>共同目标 · 时间重合</small></div>
          <div class="match-chip chip-one">目标相似 94</div>
          <div class="match-chip chip-two">时间重合 92</div>
          <div class="match-chip chip-three">方式一致 83</div>
        </div>
        <div class="matching-copy">
          <span class="section-kicker">可解释匹配</span>
          <h2>推荐的不只是“同类”，更是能一起学的人</h2>
          <p>匹配分由学习目标、可用时间、学习方式和当前阶段共同决定。每次推荐都告诉你为什么合适，也如实提示资料缺失或时间不重合。</p>
          <div class="formula-card">
            <strong>S = 0.4G + 0.35T + 0.15M + 0.1L</strong>
            <span>目标相似度</span><span>时间重合度</span><span>方式一致度</span><span>阶段相似度</span>
          </div>
          <RouterLink class="inline-link" to="/buddies">体验搭子推荐 <ArrowRight /></RouterLink>
        </div>
      </section>

      <section class="final-cta content-section">
        <div>
          <span>今天，就是新的连续第 1 天</span>
          <h2>把想学的事，变成一起做到的事</h2>
          <p>先体验完整原型，建立你的第一个目标，遇见节奏相近的学习同行者。</p>
        </div>
        <RouterLink class="light-cta" to="/auth?mode=register">免费开始 <ArrowRight /></RouterLink>
      </section>
    </main>

    <footer class="landing-footer">
      <BrandLogo />
      <p>让自律不再孤单，让学习有人同行。</p>
      <span>© 2026 学搭 StudyMate · 第一阶段交互原型</span>
    </footer>
  </div>
</template>

<style scoped>
.landing-page { min-height: 100vh; overflow: hidden; background: #fbfbfe; }
.landing-nav { position: relative; z-index: 20; display: flex; max-width: 1240px; height: 82px; align-items: center; justify-content: space-between; padding: 0 28px; margin: auto; }
.landing-nav__links { display: flex; gap: 34px; }
.landing-nav__links a { color: var(--text-secondary); font-size: 14px; font-weight: 650; text-decoration: none; }
.landing-nav__links a:hover { color: var(--primary); }
.landing-nav__actions { display: flex; align-items: center; gap: 18px; }
.login-link { color: var(--text-secondary); font-size: 14px; font-weight: 700; text-decoration: none; }
.nav-cta, .primary-cta, .light-cta { display: inline-flex; align-items: center; justify-content: center; border-radius: 11px; color: #fff; background: linear-gradient(135deg, #5b5ce2, #7763ea); box-shadow: 0 10px 26px rgba(91, 92, 226, 0.24); font-weight: 750; gap: 8px; text-decoration: none; }
.nav-cta { min-height: 40px; padding: 0 16px; font-size: 13px; }
.nav-cta svg, .primary-cta svg, .light-cta svg, .inline-link svg { width: 16px; }
.mobile-menu-button, .mobile-nav-panel { display: none; }

.hero-section { position: relative; display: grid; max-width: 1240px; min-height: 690px; align-items: center; padding: 50px 28px 80px; margin: auto; gap: 45px; grid-template-columns: 0.88fr 1.12fr; }
.hero-section::before { position: absolute; z-index: 0; top: 5%; right: -15%; width: 760px; height: 610px; border-radius: 50%; content: ''; background: radial-gradient(circle, rgba(222, 221, 255, 0.75), rgba(246, 247, 255, 0.05) 69%); }
.hero-orb { position: absolute; border-radius: 50%; filter: blur(2px); }
.hero-orb--one { top: 100px; left: -80px; width: 160px; height: 160px; background: rgba(198, 242, 246, 0.34); }
.hero-orb--two { right: 20px; bottom: 20px; width: 90px; height: 90px; background: rgba(255, 222, 191, 0.3); }
.hero-copy, .hero-visual { position: relative; z-index: 2; }
.hero-badge { display: inline-flex; align-items: center; padding: 7px 12px; border: 1px solid #dedffc; border-radius: 999px; color: #5355be; background: rgba(244, 244, 255, 0.8); font-size: 12px; font-weight: 750; gap: 7px; }
.hero-badge span { color: #8c6deb; }
.hero-copy h1 { margin: 25px 0 21px; color: #202135; font-size: clamp(44px, 5.3vw, 70px); letter-spacing: -0.07em; line-height: 1.12; }
.hero-copy h1 em { color: var(--primary); font-style: normal; }
.hero-copy > p { max-width: 530px; margin: 0; color: var(--text-secondary); font-size: 17px; line-height: 1.85; }
.hero-actions { display: flex; align-items: center; margin-top: 31px; gap: 12px; }
.primary-cta { min-height: 50px; padding: 0 22px; }
.secondary-cta { display: inline-flex; min-height: 50px; align-items: center; padding: 0 18px; border: 1px solid #e2e3ec; border-radius: 11px; color: var(--text-strong); background: #fff; font-weight: 750; gap: 7px; text-decoration: none; }
.secondary-cta svg { width: 14px; }
.hero-assurances { display: flex; flex-wrap: wrap; margin-top: 23px; color: var(--text-muted); font-size: 11px; gap: 14px; }
.hero-assurances span { display: inline-flex; align-items: center; gap: 4px; }
.hero-assurances svg { width: 13px; color: var(--success); }

.hero-visual { min-width: 0; padding: 35px 0 35px 28px; }
.preview-window { overflow: hidden; border: 1px solid rgba(222, 224, 241, 0.9); border-radius: 22px; background: #fff; box-shadow: 0 35px 90px rgba(63, 64, 111, 0.18); transform: perspective(1300px) rotateY(-3deg) rotateX(1deg); }
.preview-window__bar { display: flex; height: 35px; align-items: center; padding: 0 13px; border-bottom: 1px solid #eceef5; background: #fbfbfd; gap: 5px; }
.preview-window__bar > span { width: 7px; height: 7px; border-radius: 50%; background: #dddfea; }
.preview-window__bar > span:first-child { background: #f2a1a8; }
.preview-window__bar > span:nth-child(2) { background: #f3c780; }
.preview-window__bar > span:nth-child(3) { background: #8dd7b9; }
.preview-window__bar small { margin-left: auto; color: #a0a3b4; font-size: 8px; }
.preview-layout { display: grid; min-height: 430px; grid-template-columns: 58px 1fr; }
.preview-sidebar { display: flex; align-items: center; padding: 17px 10px; border-right: 1px solid #f0f1f6; gap: 21px; flex-direction: column; }
.preview-mark { display: grid; width: 30px; height: 30px; place-items: center; border-radius: 9px; color: #fff; background: var(--primary); font-size: 10px; font-weight: 900; }
.preview-sidebar i { width: 20px; height: 6px; border-radius: 4px; background: #e6e8ef; }
.preview-sidebar i.is-active { height: 20px; border-radius: 7px; background: #e8e9ff; box-shadow: inset 3px 0 var(--primary); }
.preview-main { padding: 25px 27px; background: #fafbfe; }
.preview-greeting { display: flex; align-items: flex-start; justify-content: space-between; }
.preview-greeting div { display: flex; flex-direction: column; }
.preview-greeting small { color: #a2a5b5; font-size: 8px; }
.preview-greeting strong { margin-top: 5px; color: #292b42; font-size: 16px; }
.preview-greeting > span { padding: 5px 8px; border-radius: 8px; color: #d67231; background: #fff0e4; font-size: 8px; font-weight: 800; }
.preview-stats { display: grid; margin-top: 18px; gap: 8px; grid-template-columns: repeat(3, 1fr); }
.preview-stats div { display: flex; padding: 11px; border: 1px solid #eef0f5; border-radius: 10px; background: #fff; flex-direction: column; }
.preview-stats small { color: #9b9eae; font-size: 7px; }
.preview-stats strong { margin-top: 3px; color: #393b51; font-size: 13px; }
.preview-content { display: grid; margin-top: 11px; gap: 9px; grid-template-columns: 1.7fr 0.8fr; }
.preview-tasks, .preview-focus { padding: 13px; border: 1px solid #eef0f5; border-radius: 11px; background: #fff; }
.preview-card-title { display: flex; justify-content: space-between; margin-bottom: 7px; }
.preview-card-title strong { color: #34364c; font-size: 9px; }
.preview-card-title span { color: var(--primary); font-size: 6px; }
.preview-tasks label { display: flex; align-items: center; padding: 7px 0; border-bottom: 1px solid #f2f3f7; gap: 8px; }
.preview-tasks label:last-child { border-bottom: 0; }
.preview-tasks label > span { display: grid; width: 11px; height: 11px; place-items: center; border: 1px solid #d9dbe7; border-radius: 4px; color: #fff; font-size: 7px; }
.preview-tasks label.done > span { border-color: var(--primary); background: var(--primary); }
.preview-tasks label i { display: flex; font-style: normal; flex-direction: column; }
.preview-tasks label b { color: #4a4c60; font-size: 7px; }
.preview-tasks label small { margin-top: 2px; color: #a9abba; font-size: 5px; }
.preview-focus { display: flex; align-items: center; text-align: center; flex-direction: column; }
.preview-focus > small { align-self: flex-start; color: #55576a; font-size: 7px; font-weight: 800; }
.mini-ring { display: grid; width: 57px; height: 57px; margin: 12px 0 8px; place-items: center; border-radius: 50%; background: conic-gradient(var(--primary) 72%, #eceef6 0); }
.mini-ring::after { position: absolute; width: 43px; height: 43px; border-radius: 50%; content: ''; background: #fff; }
.mini-ring span { z-index: 1; color: var(--primary); font-size: 10px; font-weight: 900; }
.preview-focus strong { color: #4a4c60; font-size: 7px; }
.preview-focus p { margin: 2px 0 0; color: #a6a8b8; font-size: 6px; }
.preview-bars { display: flex; height: 65px; align-items: flex-end; padding: 10px 15px 7px; margin-top: 10px; border: 1px solid #eef0f5; border-radius: 11px; background: #fff; gap: 10px; }
.preview-bars div { display: flex; height: 100%; flex: 1; align-items: center; justify-content: flex-end; gap: 3px; flex-direction: column; }
.preview-bars span { width: 100%; max-width: 19px; border-radius: 4px 4px 2px 2px; background: linear-gradient(#8582ef, #5b5ce2); }
.preview-bars small { color: #adafbd; font-size: 5px; }
.floating-match-card, .floating-check-card { position: absolute; z-index: 4; display: flex; align-items: center; border: 1px solid rgba(226, 227, 241, 0.95); background: rgba(255, 255, 255, 0.94); box-shadow: 0 16px 38px rgba(49, 51, 90, 0.16); backdrop-filter: blur(12px); }
.floating-match-card { right: -30px; bottom: 9px; padding: 12px 14px; border-radius: 15px; gap: 10px; }
.floating-match-card .avatar { width: 34px; height: 34px; border-radius: 10px; font-size: 11px; }
.floating-match-card > div { display: flex; min-width: 112px; flex-direction: column; }
.floating-match-card div small { color: #a2a5b4; font-size: 6px; }
.floating-match-card div strong { color: #3a3c51; font-size: 10px; }
.floating-match-card div em { color: #7f8294; font-size: 6px; font-style: normal; }
.floating-match-card > b { color: var(--primary); font-size: 18px; }
.floating-match-card > b small { font-size: 7px; }
.floating-check-card { top: 12px; left: -3px; padding: 9px 12px; border-radius: 13px; gap: 8px; }
.floating-check-card > span { display: grid; width: 25px; height: 25px; place-items: center; border-radius: 8px; color: #fff; background: var(--success); font-size: 10px; }
.floating-check-card div { display: flex; flex-direction: column; }
.floating-check-card strong { color: #3d3f52; font-size: 9px; }
.floating-check-card small { color: #979aaa; font-size: 6px; }

.content-section { max-width: 1184px; padding: 100px 28px; margin: auto; }
.section-intro { max-width: 680px; margin: 0 auto 46px; text-align: center; }
.section-intro > span, .section-kicker { display: inline-block; color: var(--primary); font-size: 12px; font-weight: 850; letter-spacing: 0.15em; text-transform: uppercase; }
.section-intro h2, .journey-copy h2, .matching-copy h2, .final-cta h2 { margin: 13px 0 14px; color: #242539; font-size: clamp(31px, 4vw, 45px); letter-spacing: -0.055em; line-height: 1.22; }
.section-intro p, .journey-copy > p, .matching-copy > p { margin: 0; color: var(--text-secondary); line-height: 1.8; }
.features-section { border-top: 1px solid #eeeef5; }
.feature-grid { display: grid; gap: 17px; grid-template-columns: repeat(4, 1fr); }
.feature-card { position: relative; min-height: 370px; padding: 25px 23px; overflow: hidden; border: 1px solid #e8e9f1; border-radius: 20px; background: #fff; box-shadow: 0 10px 35px rgba(46, 48, 80, 0.055); }
.feature-card::after { position: absolute; right: -40px; bottom: -45px; width: 130px; height: 130px; border-radius: 50%; content: ''; background: var(--primary-soft); opacity: 0.55; }
.feature-number { position: absolute; top: 20px; right: 21px; color: #d7d9e5; font-size: 12px; font-weight: 800; }
.feature-icon { display: grid; width: 49px; height: 49px; margin-bottom: 35px; place-items: center; border-radius: 15px; }
.feature-icon svg { width: 23px; }
.tone-violet { color: #5b5ce2; background: #eeefff; }
.tone-cyan { color: #198da1; background: #e5f7fa; }
.tone-orange { color: #cf7337; background: #fff0e5; }
.tone-green { color: #148267; background: #e5f6f0; }
.feature-card h3 { margin: 0; color: #303145; font-size: 18px; line-height: 1.5; }
.feature-card > p { min-height: 88px; margin: 12px 0 17px; color: var(--text-secondary); font-size: 13px; line-height: 1.75; }
.feature-card ul { padding: 0; margin: 0; list-style: none; }
.feature-card li { display: flex; align-items: center; margin-top: 8px; color: #6f7284; font-size: 11px; gap: 6px; }
.feature-card li svg { width: 13px; color: var(--success); }

.journey-section { display: grid; align-items: center; gap: 90px; grid-template-columns: 0.8fr 1.2fr; }
.inline-link { display: inline-flex; align-items: center; margin-top: 25px; color: var(--primary); font-weight: 800; gap: 7px; text-decoration: none; }
.journey-list { padding: 0; margin: 0; list-style: none; }
.journey-list li { display: grid; align-items: center; padding: 23px 0; border-bottom: 1px solid #eaebf2; gap: 18px; grid-template-columns: 42px 1fr 42px; }
.journey-list li > span { color: #b1b3c2; font-size: 12px; font-weight: 800; }
.journey-list li > div { display: flex; flex-direction: column; }
.journey-list strong { color: #313247; font-size: 16px; }
.journey-list p { margin: 5px 0 0; color: var(--text-secondary); font-size: 12px; line-height: 1.6; }
.journey-list li > svg { width: 20px; color: var(--primary); }

.matching-section { display: grid; align-items: center; padding-block: 120px; gap: 90px; grid-template-columns: 1.05fr 0.95fr; }
.matching-visual { position: relative; display: grid; min-height: 410px; place-items: center; border: 1px solid #e6e7f3; border-radius: 28px; background: radial-gradient(circle at 50% 50%, #f0efff, #f9faff 67%); box-shadow: 0 25px 70px rgba(61, 62, 109, 0.11); }
.match-rings, .match-rings span { position: absolute; border: 1px solid rgba(118, 107, 230, 0.14); border-radius: 50%; }
.match-rings { width: 330px; height: 330px; }
.match-rings span:first-child { inset: 45px; }
.match-rings span:nth-child(2) { inset: 90px; }
.match-rings span:nth-child(3) { inset: 130px; background: rgba(91, 92, 226, 0.07); }
.match-person { position: absolute; z-index: 2; display: flex; width: 135px; align-items: center; padding: 16px; border: 1px solid #e3e4f2; border-radius: 18px; background: #fff; box-shadow: 0 15px 34px rgba(59, 60, 104, 0.13); text-align: center; flex-direction: column; }
.match-person--me { left: 45px; }
.match-person--buddy { right: 45px; }
.match-person > span { display: grid; width: 48px; height: 48px; margin-bottom: 9px; place-items: center; border-radius: 15px; color: #fff; background: linear-gradient(145deg, #6f6aeb, #4f51cc); font-weight: 900; }
.match-person--buddy > span { background: linear-gradient(145deg, #40b9c8, #1b8ca2); }
.match-person strong { color: #3b3d51; font-size: 12px; }
.match-person small { margin-top: 4px; color: #9497a8; font-size: 7px; }
.match-line { position: relative; z-index: 3; display: flex; align-items: center; color: var(--primary); gap: 7px; }
.match-line i { width: 42px; border-top: 1px dashed #9895e9; }
.match-line b { display: grid; width: 56px; height: 56px; place-items: center; border: 5px solid #e2e1ff; border-radius: 50%; background: #fff; box-shadow: 0 10px 22px rgba(91, 92, 226, 0.2); font-size: 15px; }
.match-chip { position: absolute; z-index: 3; padding: 7px 10px; border: 1px solid #e5e6f2; border-radius: 999px; color: #696c7f; background: #fff; box-shadow: 0 7px 18px rgba(50, 51, 83, 0.08); font-size: 8px; font-weight: 750; }
.chip-one { top: 50px; left: 42%; }
.chip-two { right: 25%; bottom: 42px; }
.chip-three { bottom: 63px; left: 13%; }
.formula-card { display: grid; padding: 17px; margin-top: 24px; border: 1px solid #e2e3f6; border-radius: 14px; background: #f6f6ff; gap: 8px; grid-template-columns: repeat(2, 1fr); }
.formula-card strong { color: var(--primary-dark); font-size: 15px; grid-column: 1 / -1; }
.formula-card span { color: #797c91; font-size: 10px; }

.final-cta { display: flex; max-width: 1128px; align-items: center; justify-content: space-between; padding: 55px 58px; margin-bottom: 95px; border-radius: 28px; color: #fff; background: linear-gradient(125deg, #5051cf, #735dda 68%, #7556c8); box-shadow: 0 28px 70px rgba(78, 72, 190, 0.24); gap: 30px; }
.final-cta span { color: #d8d7ff; font-size: 11px; font-weight: 800; letter-spacing: 0.12em; }
.final-cta h2 { margin-block: 9px; color: #fff; font-size: clamp(29px, 4vw, 42px); }
.final-cta p { max-width: 620px; margin: 0; color: #e6e5ff; }
.light-cta { min-width: 145px; min-height: 50px; color: var(--primary); background: #fff; box-shadow: none; }
.landing-footer { display: flex; max-width: 1184px; align-items: center; justify-content: space-between; padding: 32px 28px 45px; margin: auto; border-top: 1px solid #e9eaf1; color: var(--text-muted); font-size: 11px; gap: 22px; }
.landing-footer p { color: var(--text-secondary); }

@media (max-width: 1020px) {
  .hero-section { grid-template-columns: 1fr; padding-top: 55px; }
  .hero-copy { max-width: 720px; text-align: center; margin: auto; }
  .hero-copy > p { margin-inline: auto; }
  .hero-actions, .hero-assurances { justify-content: center; }
  .hero-visual { max-width: 760px; width: 100%; margin: auto; padding-left: 0; }
  .feature-grid { grid-template-columns: repeat(2, 1fr); }
  .feature-card { min-height: 340px; }
  .journey-section, .matching-section { gap: 55px; }
}

@media (max-width: 760px) {
  .landing-nav { height: 68px; padding-inline: 18px; }
  .landing-nav__links, .landing-nav__actions { display: none; }
  .mobile-menu-button { display: flex; width: 40px; height: 40px; align-items: center; justify-content: center; padding: 10px; border: 1px solid #e5e6ef; border-radius: 11px; background: #fff; gap: 4px; flex-direction: column; }
  .mobile-menu-button span { width: 17px; height: 2px; border-radius: 2px; background: #55576b; }
  .mobile-nav-panel { position: absolute; top: 62px; right: 15px; display: flex; width: 200px; padding: 12px; border: 1px solid #e5e6ef; border-radius: 14px; background: #fff; box-shadow: var(--shadow-md); flex-direction: column; }
  .mobile-nav-panel a { padding: 10px; border-radius: 8px; color: var(--text-secondary); font-size: 13px; font-weight: 700; text-decoration: none; }
  .mobile-nav-panel a:hover { color: var(--primary); background: var(--primary-soft); }
  .hero-section { min-height: auto; padding: 45px 18px 75px; }
  .hero-copy h1 { margin-top: 20px; font-size: 42px; }
  .hero-copy > p { font-size: 15px; }
  .hero-actions { align-items: stretch; flex-direction: column; }
  .hero-assurances { gap: 8px 12px; }
  .hero-visual { padding-top: 15px; }
  .preview-window { transform: none; }
  .preview-layout { min-height: 330px; grid-template-columns: 42px 1fr; }
  .preview-main { padding: 16px 13px; }
  .preview-content { grid-template-columns: 1fr; }
  .preview-focus, .preview-bars { display: none; }
  .floating-match-card { right: -6px; bottom: -15px; }
  .floating-check-card { top: -8px; left: -4px; }
  .content-section { padding: 72px 18px; }
  .feature-grid { grid-template-columns: 1fr; }
  .feature-card { min-height: auto; }
  .feature-card > p { min-height: auto; }
  .journey-section, .matching-section { grid-template-columns: 1fr; }
  .matching-visual { min-height: 330px; order: 2; }
  .match-person { width: 112px; padding: 12px; }
  .match-person--me { left: 15px; }
  .match-person--buddy { right: 15px; }
  .match-line i { width: 20px; }
  .final-cta { align-items: flex-start; padding: 40px 26px; margin-inline: 14px; margin-bottom: 65px; border-radius: 22px; flex-direction: column; }
  .light-cta { width: 100%; }
  .landing-footer { align-items: flex-start; padding-inline: 18px; flex-direction: column; }
  .landing-footer p { margin: 0; }
}
</style>
