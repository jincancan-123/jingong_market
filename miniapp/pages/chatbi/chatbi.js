const { request } = require('../../utils/request.js');

Page({
  data: {
    messages: [],
    inputValue: '',
    loading: false,
    sessionId: ''
  },

  onLoad() {
    this.setData({
      sessionId: `miniapp-${Date.now()}`
    });

    this._pushMessage({
      role: 'assistant',
      content: '您好，我可以帮你做自然语言查数。比如输入“上周海天酱油天猫销量走势”试试看。'
    });
  },

  onInput(e) {
    this.setData({
      inputValue: e.detail.value
    });
  },

  sendMessage() {
    const question = (this.data.inputValue || '').trim();
    if (!question) {
      wx.showToast({
        title: '请输入查询内容',
        icon: 'none'
      });
      return;
    }

    this._pushMessage({
      role: 'user',
      content: question
    });

    this.setData({
      inputValue: '',
      loading: true
    });

    request('/chatbi/ask', 'POST', {
      question,
      session_id: this.data.sessionId,
      history: this.data.messages.map(item => ({
        question: item.role === 'user' ? item.content : '',
        answer: item.role === 'assistant' ? item.content : ''
      })).filter(item => item.question || item.answer)
    })
      .then((res) => {
        const answer = res && res.answer ? res.answer : '暂时没有返回有效结论。';
        this._pushMessage({
          role: 'assistant',
          content: answer
        });
      })
      .catch((err) => {
        console.error('ChatBI 请求失败', err);
        this._pushMessage({
          role: 'assistant',
          content: '抱歉，当前查询失败，请稍后再试。'
        });
      })
      .finally(() => {
        this.setData({ loading: false });
        this._scrollToBottom();
      });
  },

  _pushMessage(message) {
    const messages = this.data.messages.concat(message);
    this.setData({ messages });
    this._scrollToBottom();
  },

  _scrollToBottom() {
    wx.nextTick(() => {
      const query = wx.createSelectorQuery();
      query.select('#chat-list').boundingClientRect();
      query.exec((res) => {
        if (res && res[0]) {
          const scrollHeight = res[0].height;
          wx.pageScrollTo({
            scrollTop: scrollHeight + 1000,
            duration: 0
          });
        }
      });
    });
  }
});
