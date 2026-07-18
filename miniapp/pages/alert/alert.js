const { request } = require("../../utils/request.js");

Page({
  data: {
    alertList: []
  },
  onLoad() {
    this.loadAlert();
  },
  loadAlert() {
    request("/miniapp/alert/subscribe")
      .then(res => {
        this.setData({
          alertList: res.data
        });
      })
      .catch(error => {
        console.error("预警接口请求失败：", error);
        this.setData({ alertList: [] });
        wx.showToast({
          title: "预警加载失败",
          icon: "none"
        });
      });
  }
});