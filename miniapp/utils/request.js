// utils/request.js
const BASE_URL = "http://127.0.0.1:8000";

function request(url, method = "GET", data = {}) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: BASE_URL + url,
      method: method,
      data: data,
      header: {
        "content-type": "application/json"
      },
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(res.data);
        } else {
          reject(res);
        }
      },
      fail: (err) => {
        reject(err);
      }
    })
  })
}

module.exports = { request }