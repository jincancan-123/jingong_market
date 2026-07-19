const { request } = require("../../utils/request.js");

Page({
  data: {
    list: [],
    page: 1,
    pageSize: 8,
    total: 0,
    platform: "",
    price: "",
    brand: ""
  },
  onLoad() {
    this.loadProducts();
  },
  onPlatformInput(e) {
    this.setData({ platform: e.detail.value });
  },
  onBrandInput(e) {
    this.setData({ brand: e.detail.value });
  },
  onPriceChange(e) {
    this.setData({ price: e.detail.value });
  },
  search() {
    this.setData({ page: 1 });
    this.loadProducts();
  },
  loadProducts() {
    const { page, pageSize, platform, price, brand } = this.data;
    let url = `/miniapp/product/list?page=${page}&page_size=${pageSize}`;
    if (platform) url += `&platform=${encodeURIComponent(platform)}`;
    if (price) url += `&price=${price}`;
    if (brand) url += `&brand=${encodeURIComponent(brand)}`;

    request(url)
      .then((res) => {
        this.setData({ list: res.data.items || [], total: res.data.total || 0 });
      })
      .catch(() => {
        this.setData({ list: [] });
      });
  },
  goDetail(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: `/pages/product/detail/detail?id=${id}` });
  },
  prevPage() {
    if (this.data.page > 1) {
      this.setData({ page: this.data.page - 1 });
      this.loadProducts();
    }
  },
  nextPage() {
    const maxPage = Math.ceil(this.data.total / this.data.pageSize);
    if (this.data.page < maxPage) {
      this.setData({ page: this.data.page + 1 });
      this.loadProducts();
    }
  }
});
