const { request } = require("../../utils/request.js");

Page({
  data: {
    platform: "天猫",
    keyword: "",
    brandKeywords: "",
    hotKeywords: "",
    logs: []
  },
  onLoad() {
    this.loadLogs();
  },
  onPlatformInput(e) {
    this.setData({ platform: e.detail.value });
  },
  onKeywordInput(e) {
    this.setData({ keyword: e.detail.value });
  },
  onBrandInput(e) {
    this.setData({ brandKeywords: e.detail.value });
  },
  onHotInput(e) {
    this.setData({ hotKeywords: e.detail.value });
  },
  runCrawl() {
    const keyword = this.data.keyword.trim();
    if (!keyword) {
      wx.showToast({ title: "请输入关键词", icon: "none" });
      return;
    }

    request("/miniapp/crawl/run", "POST", {
      platform: this.data.platform || "天猫",
      keyword: keyword
    })
      .then(() => {
        wx.showToast({ title: "采集任务已提交", icon: "success" });
        this.loadLogs();
      })
      .catch(() => {
        wx.showToast({ title: "采集任务提交失败", icon: "none" });
      });
  },
  runCompetitor() {
    const brandKeywords = this.data.brandKeywords
      .split(/[,，;；\s]+/)
      .map((item) => item.trim())
      .filter(Boolean);

    if (brandKeywords.length === 0) {
      wx.showToast({ title: "请输入品牌关键词", icon: "none" });
      return;
    }

    request("/miniapp/crawl/competitor", "POST", {
      platform: this.data.platform || "天猫",
      brand_keywords: brandKeywords
    })
      .then(() => {
        wx.showToast({ title: "竞品采集已提交", icon: "success" });
        this.loadLogs();
      })
      .catch(() => {
        wx.showToast({ title: "竞品采集失败", icon: "none" });
      });
  },
  runOpinion() {
    const hotKeywords = this.data.hotKeywords
      .split(/[,，;；\s]+/)
      .map((item) => item.trim())
      .filter(Boolean);

    if (hotKeywords.length === 0) {
      wx.showToast({ title: "请输入热词", icon: "none" });
      return;
    }

    request("/miniapp/crawl/opinion", "POST", {
      hot_keywords: hotKeywords
    })
      .then(() => {
        wx.showToast({ title: "舆情采集已提交", icon: "success" });
        this.loadLogs();
      })
      .catch(() => {
        wx.showToast({ title: "舆情采集失败", icon: "none" });
      });
  },
  loadLogs() {
    request("/miniapp/crawl/log", "GET")
      .then((res) => {
        const logs = res && res.data ? res.data : [];
        this.setData({ logs: Array.isArray(logs) ? logs : [] });
      })
      .catch(() => {
        this.setData({ logs: [] });
      });
  }
});
