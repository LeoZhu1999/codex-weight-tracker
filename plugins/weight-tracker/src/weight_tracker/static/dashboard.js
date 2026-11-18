(() => {
  const token = window.__WEIGHT_TRACKER_TOKEN__;
  const DAY = 86400000;
  const $ = (selector) => document.querySelector(selector);
  const chartHost = $('#chart');
  const chart = echarts.init(chartHost, null, {renderer: 'canvas'});
  const state = {language: localStorage.getItem('weight-tracker-language') || 'zh', payload: null, preset: 30, start: null, end: null, y: null, suppress: false, ignoreDataZoomUntil: 0};
  const copy = {
    zh: {title:'体重趋势', help:'操作说明', latest:'最新日均', bmiLabel:'当前 BMI', change:'7日均值变化', range7:'7日',range30:'30日',range90:'90日',range180:'半年',range365:'1年',all:'全部', autoY:'自动纵轴', reset:'恢复默认', refresh:'刷新', export:'导出 PNG', exit:'退出服务', custom:'自定义', day:'天', observed:'有效称重日', raw:'日均体重', average:'7日滚动平均', helpTitle:'操作说明', noData:'暂无体重记录', bmiStandard:{china_adult:'中国成人标准',who_adult:'WHO 成人标准'}, category:{Underweight:'偏瘦',Normal:'正常',Overweight:'超重',Obesity:'肥胖'}, tips:['拖动画布可平移时间范围；鼠标滚轮缩放横轴。','拖动底部时间轴可缩放横轴，双击底轴恢复最近 30 天。','拖动右侧体重轴或按 Shift + 滚轮可缩放纵轴；双击右轴恢复自动纵轴。','点击图例可隐藏或显示曲线；悬浮十字光标可查看具体数据。']},
    en: {title:'Weight trend', help:'Help', latest:'Latest daily average', bmiLabel:'Current BMI', change:'7-day average change', range7:'7D',range30:'30D',range90:'90D',range180:'6M',range365:'1Y',all:'All', autoY:'Auto Y', reset:'Reset', refresh:'Refresh', export:'Export PNG', exit:'Exit service', custom:'Custom', day:'days', observed:'observed days', raw:'Daily average', average:'7-day rolling average', helpTitle:'How to use', noData:'No weight records yet', bmiStandard:{china_adult:'China adult standard',who_adult:'WHO adult standard'}, category:{Underweight:'Underweight',Normal:'Normal',Overweight:'Overweight',Obesity:'Obesity'}, tips:['Drag the plot to pan time; use the wheel to zoom the horizontal axis.','Drag the bottom time axis to scale it; double-click it to restore the last 30 days.','Drag the right weight axis or use Shift + wheel to scale it; double-click it for auto Y.','Click a legend item to show or hide a line; hover the crosshair for details.']}
  };
  const t = (key) => copy[state.language][key] || key;
  const ts = (date) => new Date(`${date}T12:00:00`).getTime();
  const api = (path, options = {}) => fetch(path, {...options, headers: {'X-Weight-Tracker-Token': token, ...(options.headers || {})}});
  function visiblePoints() { return (state.payload?.points || []).filter(p => !state.start || (ts(p.date) >= state.start && ts(p.date) <= state.end)); }
  function yBounds() { const values = visiblePoints().flatMap(p => [p.weight, p.rolling_7d].filter(Number.isFinite)); if (!values.length) return null; let lo = Math.min(...values), hi = Math.max(...values); const pad = Math.max(.25, (hi - lo || 1) * .14); return {min: +(lo - pad).toFixed(2), max: +(hi + pad).toFixed(2)}; }
  function normalizedY() { return state.y || yBounds(); }
  function updateText() {
    document.documentElement.lang = state.language === 'zh' ? 'zh-CN' : 'en';
    document.title = t('title');
    document.querySelectorAll('[data-i18n]').forEach(node => { node.textContent = t(node.dataset.i18n); });
    $('#language').textContent = state.language === 'zh' ? 'EN' : '中文';
    $('#help-list').innerHTML = t('tips').map(item => `<li>${item}</li>`).join('');
  }
  function applyRange(days) {
    const points = state.payload?.points || []; if (!points.length) return;
    const last = ts(points.at(-1).date), first = ts(points[0].date);
    state.preset = days; state.end = last; state.start = days === 'all' ? first : Math.max(first, last - (days - 1) * DAY); state.y = null;
    render();
  }
  function markRange() { document.querySelectorAll('[data-range]').forEach(button => button.classList.toggle('active', String(state.preset) === button.dataset.range)); $('#range-state').textContent = state.preset === 'custom' ? t('custom') : ''; }
  function render() {
    const payload = state.payload; updateText(); markRange();
    if (!payload || !payload.points.length) { chart.clear(); return; }
    const bounds = normalizedY(); const unit = payload.unit;
    state.suppress = true; state.ignoreDataZoomUntil = Date.now() + 1000;
    chart.setOption({animation:false, backgroundColor:'transparent', grid:{left:64,right:70,top:42,bottom:56,containLabel:false}, legend:{top:5,left:10,itemGap:18,textStyle:{color:'#315a54'},data:[t('raw'),t('average')]}, tooltip:{trigger:'axis',axisPointer:{type:'cross',label:{backgroundColor:'#0f766e'}},formatter(params){const point = payload.points.find(p => ts(p.date) === params[0].value[0]); if (!point) return ''; const locale = state.language === 'zh' ? 'zh-CN' : 'en-US'; const date = new Intl.DateTimeFormat(locale,{dateStyle:'medium'}).format(new Date(point.date+'T12:00:00')); return `<b>${date}</b><br>${t('raw')}: ${point.weight.toFixed(2)} ${unit}<br>${t('average')}: ${point.rolling_7d?.toFixed(2) ?? '—'} ${unit}<br>${point.measurements} ${t('observed')}`;}}, xAxis:{type:'time',boundaryGap:false,axisLine:{lineStyle:{color:'#9ebdb7'}},axisLabel:{color:'#52716c',hideOverlap:true,formatter:value => new Intl.DateTimeFormat(state.language === 'zh'?'zh-CN':'en-US',{month:'short',day:'numeric'}).format(new Date(value))},min:state.start,max:state.end}, yAxis:{type:'value',name:unit,scale:true,min:bounds?.min,max:bounds?.max,axisLine:{show:true,lineStyle:{color:'#9ebdb7'}},axisLabel:{color:'#52716c'},splitLine:{lineStyle:{color:'#e2efec'}}}, dataZoom:[{type:'inside',xAxisIndex:0,filterMode:'filter',zoomOnMouseWheel:true,moveOnMouseMove:true,moveOnMouseWheel:false,preventDefaultMouseMove:false},{type:'slider',xAxisIndex:0,height:16,bottom:10,brushSelect:false,showDetail:false,handleSize:12,borderColor:'#cde4df',fillerColor:'#0f766e33',dataBackground:{lineStyle:{color:'#0f766e'},areaStyle:{color:'#0f766e22'}}}], series:[{name:t('raw'),type:'line',showSymbol:true,symbolSize:7,smooth:false,connectNulls:false,itemStyle:{color:'#0f766e'},lineStyle:{width:3,color:'#0f766e'},data:payload.points.map(p=>[ts(p.date),p.weight])},{name:t('average'),type:'line',showSymbol:false,smooth:false,lineStyle:{width:2,type:'dashed',color:'#f59e0b'},data:payload.points.map(p=>[ts(p.date),p.rolling_7d])}]},{notMerge:true,lazyUpdate:false});
    state.suppress = false;
  }
  function refreshMetrics() { const d = state.payload; const latest = d.latest; $('#latest').textContent = latest ? `${latest.weight.toFixed(2)} ${d.unit}` : '—'; $('#latest-note').textContent = latest?.date || ''; $('#bmi').textContent = d.bmi.value ?? '—'; $('#bmi-note').textContent = d.bmi.category ? `${t('category')[d.bmi.category]} · ${t('bmiStandard')[d.bmi.standard]}` : ''; $('#change').textContent = d.seven_day_change ? `${d.seven_day_change.display > 0 ? '+' : ''}${d.seven_day_change.display.toFixed(2)} ${d.unit}` : '—'; $('#change-note').textContent = d.seven_day_change ? `${d.seven_day_change.current_days} / ${d.seven_day_change.previous_days} ${t('observed')}` : ''; $('#updated').textContent = new Intl.DateTimeFormat(state.language==='zh'?'zh-CN':'en-US',{dateStyle:'medium',timeStyle:'short'}).format(new Date()); }
  async function load(preserve = false) { const response = await fetch('/api/dashboard',{cache:'no-store'}); if (!response.ok) throw Error(await response.text()); const old = {preset:state.preset,start:state.start,end:state.end}; state.payload = await response.json(); if (!preserve || old.preset !== 'custom') applyRange(old.preset || 30); else { state.preset='custom'; const points=state.payload.points; state.start=Math.max(ts(points[0].date),old.start); state.end=Math.min(ts(points.at(-1).date),old.end); render(); } refreshMetrics(); }
  function scaleY(factor) { const current = normalizedY(); if (!current) return; const center=(current.min+current.max)/2, half=Math.max(.2,(current.max-current.min)*factor/2); state.y={min:+(center-half).toFixed(2),max:+(center+half).toFixed(2)}; render(); }
  let drag = null;
  chartHost.addEventListener('pointerdown', event => { const rect=chartHost.getBoundingClientRect(); if (event.clientX > rect.right-72) drag={kind:'y',x:event.clientX,y:event.clientY,bounds:normalizedY()}; else if (event.clientY > rect.bottom-52) drag={kind:'x',x:event.clientX,y:event.clientY,start:state.start,end:state.end}; });
  window.addEventListener('pointermove', event => { if (!drag) return; if (drag.kind==='y') { const factor=Math.exp((event.clientY-drag.y)/150); const center=(drag.bounds.min+drag.bounds.max)/2, half=Math.max(.2,(drag.bounds.max-drag.bounds.min)*factor/2); state.y={min:+(center-half).toFixed(2),max:+(center+half).toFixed(2)}; render(); } else { const factor=Math.exp((event.clientX-drag.x)/280); const mid=(drag.start+drag.end)/2, half=Math.max(DAY,(drag.end-drag.start)*factor/2); state.start=mid-half; state.end=mid+half; state.preset='custom'; state.y=null; render(); } });
  window.addEventListener('pointerup', () => { drag=null; });
  chartHost.addEventListener('dblclick', event => { const rect=chartHost.getBoundingClientRect(); if (event.clientX > rect.right-72) { state.y=null; render(); } else if (event.clientY > rect.bottom-52) applyRange(30); });
  chartHost.addEventListener('wheel', event => { if (!event.shiftKey) return; event.preventDefault(); scaleY(event.deltaY > 0 ? 1.16 : .86); }, {passive:false});
  chart.on('datazoom', () => { if (state.suppress || Date.now() < state.ignoreDataZoomUntil || !state.payload) return; const option=chart.getOption().dataZoom?.[0] || {}; if (Number.isFinite(option.startValue) && Number.isFinite(option.endValue)) { state.start=option.startValue; state.end=option.endValue; state.preset='custom'; state.y=null; refreshMetrics(); markRange(); } });
  $('#ranges').addEventListener('click', event => { const button=event.target.closest('[data-range]'); if (button) applyRange(button.dataset.range === 'all' ? 'all' : Number(button.dataset.range)); });
  $('#auto-y').onclick=()=>{state.y=null;render();}; $('#reset').onclick=()=>applyRange(30); $('#refresh').onclick=()=>load(true).catch(error=>alert(error.message)); $('#export').onclick=()=>{const link=document.createElement('a');link.download=`weight-trend-${state.payload.latest?.date || 'chart'}.png`;link.href=chart.getDataURL({pixelRatio:2,backgroundColor:'#ffffff'});link.click();};
  $('#language').onclick=()=>{state.language=state.language==='zh'?'en':'zh';localStorage.setItem('weight-tracker-language',state.language);refreshMetrics();render();}; $('#help').onclick=()=>$('#help-dialog').showModal(); $('#shutdown').onclick=async()=>{await api('/api/shutdown',{method:'POST'});document.body.innerHTML='<main class="closed">Dashboard service stopped. You can close this tab.</main>';};
  const beat=()=>api('/api/heartbeat',{method:'POST'}).catch(()=>{}); beat(); setInterval(beat,15000); new ResizeObserver(()=>chart.resize()).observe(chartHost);
  load().catch(error=>{chart.clear();chartHost.textContent=error.message;});
})();
