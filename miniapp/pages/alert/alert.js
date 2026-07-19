const { request, getToken } = require("../../utils/request.js");

Page({
  data: {
    alertList: []
  },
  onLoad() {
    this.loadAlert();
  },
  loadAlert() {
    if (!getToken()) {
      wx.redirectTo({
        url: "/pages/login/login"
      });
      return;
    }

    request("/miniapp/alert/list", "GET")
      .then((res) => {
        const items = res && res.data && res.data.alert_items ? res.data.alert_items : [];
        this.setData({
          alertList: items
        });
      })
      .catch((error) => {
        console.error("预警接口请求失败：", error);
        this.setData({ alertList: [] });
        wx.showToast({
          title: "预警加载失败",
          icon: "none"
        });
      });
  },
  toggleSubscribe(event) {
    const category = event.currentTarget.dataset.category;
    const index = this.data.alertList.findIndex(item => item.brand === category);
    if (index === -1) {
      return;
    }

    const item = this.data.alertList[index];
    const action = item.subscribed ? "cancel" : "subscribe";

    request("/miniapp/alert/subscribe", "POST", {
      category: category,
      action: action
    })
      .then(() => {
        const nextList = [...this.data.alertList];
        nextList[index] = {
          ...item,
          subscribed: !item.subscribed
        };
        this.setData({ alertList: nextList });
        wx.showToast({
          title: action === "cancel" ? "已取消订阅" : "订阅成功",
          icon: "success"
        });
      })
      .catch((error) => {
        console.error("订阅接口请求失败：", error);
        wx.showToast({
          title: "订阅失败",
          icon: "none"
        });
      });
  }
});