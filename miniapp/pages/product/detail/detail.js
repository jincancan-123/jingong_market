const { request } = require("../../../utils/request.js");
import * as echarts from '../../../ec-canvas/echarts';

Page({
  data: {
    product: {},
    xAxis: [],
    priceTrend: [],
    salesTrend: [],
    chart: { onInit: null }
  },
  onLoad(options) {
    if (options.id) {
      this.loadDetail(options.id);
      this.setData({ chart: { onInit: this.initChart.bind(this) } });
    }
  },
  loadDetail(id) {
    request(`/miniapp/product/${id}`)
      .then((res) => {
        this.setData({
          product: res.data.product || {},
          xAxis: res.data.x_axis || [],
          priceTrend: res.data.price_trend || [],
          salesTrend: res.data.sales_trend || []
        });
      })
      .catch(() => {
        wx.showToast({ title: "详情加载失败", icon: "none" });
      });
  },
  initChart(canvas, width, height, dpr) {
    const chart = echarts.init(canvas, null, { width, height, devicePixelRatio: dpr });
    canvas.setChart(chart);
    const option = {
      tooltip: { trigger: "axis" },
      legend: { data: ["价格", "销量"] },
      xAxis: { type: "category", data: this.data.xAxis },
      yAxis: [{ type: "value" }, { type: "value" }],
      series: [
        { name: "价格", type: "line", data: this.data.priceTrend, smooth: true },
        { name: "销量", type: "line", data: this.data.salesTrend, smooth: true, yAxisIndex: 1 }
      ]
    };
    chart.setOption(option);
    return chart;
  }
});