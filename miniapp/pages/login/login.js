const { request, saveToken } = require("../../utils/request.js");

Page({
  data: {
    username: "",
    password: ""
  },
  onLoad() {
    wx.setNavigationBarTitle({ title: "登录" });
  },
  onInput(event, key) {
    const value = event.detail.value;
    this.setData({ [key]: value });
  },
  bindUsernameInput(e) {
    this.onInput(e, "username");
  },
  bindPasswordInput(e) {
    this.onInput(e, "password");
  },
  doLogin() {
    const { username, password } = this.data;
    if (!username || !password) {
      wx.showToast({ title: "请输入账号和密码", icon: "none" });
      return;
    }

    request("/miniapp/login", "POST", { username, password })
      .then((res) => {
        if (res && res.data && res.data.token) {
          saveToken(res.data.token);
          wx.switchTab({ url: "/pages/index/index" });
        }
      })
      .catch((err) => {
        console.error(err);
        wx.showToast({ title: "登录失败", icon: "none" });
      });
  }
});
