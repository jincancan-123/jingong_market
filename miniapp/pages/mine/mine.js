const { request, clearToken } = require("../../utils/request.js");

Page({
  data: {
    crawlLogs: [],
    alerts: [],
    report: {},
    userName: ""
  },
  onLoad() {
    this.loadMine();
  },
  loadMine() {
    request("/miniapp/crawl/log?page=1&page_size=5")
      .then((res) => {
        this.setData({ crawlLogs: res.data.items || [] });
      })
      .catch(() => {
        this.setData({ crawlLogs: [] });
      });

    request("/miniapp/alert/list")
      .then((res) => {
        this.setData({ alerts: res.data.alert_items || [] });
      })
      .catch(() => {
        this.setData({ alerts: [] });
      });

    request("/miniapp/report/daily")
      .then((res) => {
        this.setData({ report: res.data.report || {}, userName: res.data.operator || "用户" });
      })
      .catch(() => {
        this.setData({ report: {}, userName: "用户" });
      });
  },
  logout() {
    clearToken();
    wx.redirectTo({ url: "/pages/login/login" });
  }
});