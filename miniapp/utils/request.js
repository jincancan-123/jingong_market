// utils/request.js
const BASE_URL = "http://127.0.0.1:8000";

function getToken() {
  try {
    return wx.getStorageSync("miniapp_token") || "";
  } catch (e) {
    return "";
  }
}

function saveToken(token) {
  try {
    wx.setStorageSync("miniapp_token", token);
  } catch (e) {
    console.error("保存 token 失败", e);
  }
}

function clearToken() {
  try {
    wx.removeStorageSync("miniapp_token");
  } catch (e) {
    console.error("清除 token 失败", e);
  }
}

function request(url, method = "GET", data = {}) {
  return new Promise((resolve, reject) => {
    const token = getToken();
    const headers = {
      "content-type": "application/json"
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
      headers["X-Token"] = token;
    }

    wx.request({
      url: BASE_URL + url,
      method: method.toUpperCase(),
      data: data,
      header: headers,
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(res.data);
        } else if (res.statusCode === 401) {
          const pages = getCurrentPages();
          const currentPage = pages[pages.length - 1];
          const route = currentPage && currentPage.route;
          if (route !== "pages/login/login") {
            clearToken();
            wx.redirectTo({
              url: "/pages/login/login"
            });
          }
          reject(res);
        } else {
          reject(res);
        }
      },
      fail: (err) => {
        reject(err);
      }
    });
  });
}

module.exports = { request, getToken, saveToken, clearToken };