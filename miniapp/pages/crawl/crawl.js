const { request } = require("../../utils/request.js");
import * as echarts from '../../ec-canvas/echarts';

Page({
  data: {
    keyword: "",
    logs: [],
    page: 1,
    pageSize: 8,
    total: 0,
    chartData: {
      xAxis: [],
      priceSeries: [],
      salesSeries: []
    },
    trendChart: { onInit: null }
  },
  onLoad() {
    this.loadLogs();
    this.loadTrend();
    this.setData({ trendChart: { onInit: this.initTrendChart.bind(this) } });
  },
  onKeywordInput(e) {
    this.setData({ keyword: e.detail.value });
  },
  runCrawl() {
    const keyword = this.data.keyword.trim();
    if (!keyword) {
      wx.showToast({ title: "请输入关键词", icon: "none" });
      return;
    }
    request("/miniapp/crawl/run", "POST", { platform: "天猫", keyword })
      .then(() => {
        wx.showToast({ title: "任务已提交", icon: "success" });
        this.loadLogs();
      })
      .catch(() => {
        wx.showToast({ title: "任务提交失败", icon: "none" });
      });
  },
  loadLogs() {
    request(`/miniapp/crawl/log?page=${this.data.page}&page_size=${this.data.pageSize}`)
      .then((res) => {
        this.setData({ logs: res.data.items || [], total: res.data.total || 0 });
      })
      .catch(() => {
        this.setData({ logs: [] });
      });
  },
  loadTrend() {
    request("/miniapp/report/trend")
      .then((res) => {
        this.setData({ chartData: res.data });
      })
      .catch(() => {
        this.setData({ chartData: { xAxis: [], priceSeries: [], salesSeries: [] } });
      });
  },
  initTrendChart(canvas, width, height, dpr) {
    const chart = echarts.init(canvas, null, { width, height, devicePixelRatio: dpr });
    canvas.setChart(chart);
    const data = this.data.chartData;
    const option = {
      backgroundColor: "transparent",
      tooltip: { trigger: "axis" },
      legend: { data: ["均价", "销量"], textStyle: { color: "#333" } },
      xAxis: { type: "category", data: data.xAxis || [] },
      yAxis: [{ type: "value" }, { type: "value" }],
      series: [
        { name: "均价", type: "line", data: data.priceSeries || [], smooth: true },
        { name: "销量", type: "line", data: data.salesSeries || [], smooth: true, yAxisIndex: 1 }
      ]
    };
    chart.setOption(option);
    return chart;
  }
});
