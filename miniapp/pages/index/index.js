import * as echarts from '../../ec-canvas/echarts';
const { request } = require("../../utils/request.js");

Page({
  data: {
    homeData: {},
    // 三个图表实例挂载对象
    pie: { onInit: null },
    bar: { onInit: null },
    barH: { onInit: null }
  },
  onLoad() {
    this.loadHomeData();
    // 绑定图表初始化钩子函数
    this.setData({
      pie: { onInit: this.initPieChart.bind(this) },
      bar: { onInit: this.initBarChart.bind(this) },
      barH: { onInit: this.initBarHChart.bind(this) }
    })
  },
  loadHomeData() {
    request("/miniapp/home")
      .then(res => {
        console.log("接口返回数据：", res);
        this.setData({
          homeData: res.data
        });
        // 已删除：手动调用initChart的setTimeout代码，这是报错根源
      })
      .catch(error => {
        console.error("首页接口请求失败：", error);
        this.setData({
          homeData: {
            total_product: "--",
            total_gmv: "--",
            total_sales: "--",
            update_time: "--",
            top_brand: [],
            platform_sales: [],
            price_range: []
          }
        });
        wx.showToast({
          title: "数据加载失败",
          icon: "none"
        });
      });
  },
  goAlert() {
    wx.navigateTo({
      url: "/pages/alert/alert"
    });
  },

  goChatBI() {
    wx.navigateTo({
      url: "/pages/chatbi/chatbi"
    });
  },

  // 饼图：平台销量分布
  initPieChart(canvas, width, height, dpr) {
    const chart = echarts.init(canvas, null, { width, height, devicePixelRatio: dpr });
    canvas.setChart(chart);
    const platform = this.data.homeData.platform_sales || [];
    const option = {
      backgroundColor: 'transparent',
      textStyle: { color: '#fff' },
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie',
        radius: '60%',
        data: platform.map(v => ({ name: v.platform, value: v.sales }))
      }]
    };
    chart.setOption(option);
    return chart;
  },

  // 柱状图：价格区间统计
  initBarChart(canvas, width, height, dpr) {
    const chart = echarts.init(canvas, null, { width, height, devicePixelRatio: dpr });
    canvas.setChart(chart);
    const price = this.data.homeData.price_range || [];
    const option = {
      backgroundColor: 'transparent',
      textStyle: { color: '#fff' },
      xAxis: { type: 'category', data: price.map(v => v.range), axisLine: { lineStyle: { color: '#fff' } } },
      yAxis: { type: 'value', axisLine: { lineStyle: { color: '#fff' } } },
      series: [{ type: 'bar', data: price.map(v => v.count), color: '#4fc3f7' }]
    };
    chart.setOption(option);
    return chart;
  },

  // 横向条形图：品牌商品数量
  initBarHChart(canvas, width, height, dpr) {
    const chart = echarts.init(canvas, null, { width, height, devicePixelRatio: dpr });
    canvas.setChart(chart);
    const brand = this.data.homeData.top_brand || [];
    const option = {
      backgroundColor: 'transparent',
      textStyle: { color: '#fff' },
      xAxis: { type: 'value', axisLine: { lineStyle: { color: '#fff' } } },
      yAxis: { type: 'category', data: brand.map(v => v.brand), axisLine: { lineStyle: { color: '#fff' } } },
      series: [{ type: 'bar', data: brand.map(v => v.count), color: '#4fc3f7' }]
    };
    chart.setOption(option);
    return chart;
  }
});