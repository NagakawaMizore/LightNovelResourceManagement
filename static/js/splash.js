/**
 * 首屏帘幕引导页交互（FR-03 / FR-04 / FR-05）
 *
 * FR-03: 鼠标 hover "进入页面"按钮 → 雾化遮罩平滑消退露出高清原图；移开平滑恢复
 * FR-04: 点击按钮 → 帘幕 translateY(-100%) 上滑出视窗，transitionend 后 display:none 并解锁滚动
 * FR-05: 点击后立即写入 sessionStorage 标记，本会话不再弹出
 */
(function () {
  var curtain = document.getElementById('splash-curtain');
  var enterBtn = document.getElementById('splash-enter-btn');
  if (!curtain || !enterBtn) return;

  // FR-03: 悬浮交互 —— 消除/恢复雾化
  function reveal() { curtain.classList.add('revealed'); }
  function unreveal() { curtain.classList.remove('revealed'); }

  // 进入按钮：mouseenter / mouseover 双监听，兼容真实指针与合成事件
  enterBtn.addEventListener('mouseenter', reveal);
  enterBtn.addEventListener('mouseover', reveal);
  // 指针离开按钮（含离开窗口）：恢复雾化
  enterBtn.addEventListener('mouseleave', unreveal);
  // 冒泡兜底：鼠标移到帘幕内按钮以外的任何区域 → 恢复雾化
  curtain.addEventListener('mouseover', function (e) {
    if (!enterBtn.contains(e.target)) unreveal();
  });

  // FR-04 + FR-05: 进入转场
  enterBtn.addEventListener('click', function () {
    // FR-05: 点击进入后立即写入会话标记
    sessionStorage.setItem('splash_entered', 'true');

    // FR-04: 触发 GPU 加速向上滑出动效
    curtain.classList.add('active');

    var finished = false;
    var finish = function () {
      if (finished) return;
      finished = true;
      curtain.style.display = 'none';            // 完全离开视窗后彻底移除，不再阻挡底层交互
      document.body.classList.remove('splash-locked');  // 解禁主文档滚动
    };

    curtain.addEventListener('transitionend', function (e) {
      if (e.propertyName === 'transform') finish();
    }, { once: true });

    // 兜底：transitionend 意外未触发（如动画被中断）时也要解锁页面
    setTimeout(finish, 900);
  });
})();
