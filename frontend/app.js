const API_BASE_URL = 'http://localhost:8000';

class CryptoApp extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            message: '載入中...',
            coins: [],
            timeframes: [],
            loading: false,
            trainingStatus: null
        };
    }

    componentDidMount() {
        this.checkBackend();
        this.fetchCoins();
    }

    checkBackend = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/health`);
            if (response.ok) {
                this.setState({ message: '✅ 系統已連接！' });
            }
        } catch (error) {
            this.setState({ message: '❌ 後端無法連接: ' + error.message });
        }
    }

    fetchCoins = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/coins`);
            const data = await response.json();
            this.setState({
                coins: data.coins,
                timeframes: data.timeframes
            });
        } catch (error) {
            console.error('Error fetching coins:', error);
        }
    }

    startTraining = async () => {
        this.setState({ loading: true });
        try {
            const response = await fetch(`${API_BASE_URL}/train-models`, {
                method: 'POST'
            });
            const data = await response.json();
            this.setState({ message: '🔄 訓練已啟動...' });
            
            // 每2秒檢查訓練進度
            this.trainingInterval = setInterval(this.checkTrainingStatus, 2000);
        } catch (error) {
            this.setState({ message: '❌ 訓練啟動失敗: ' + error.message });
        }
    }

    checkTrainingStatus = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/training-status`);
            const status = await response.json();
            this.setState({ trainingStatus: status });
            
            if (status.status !== 'in_progress') {
                clearInterval(this.trainingInterval);
                this.setState({ 
                    loading: false,
                    message: '✅ 訓練完成！'
                });
            }
        } catch (error) {
            console.error('Error checking training status:', error);
        }
    }

    render() {
        const { message, coins, timeframes, loading, trainingStatus } = this.state;

        return (
            React.createElement('div', { style: styles.container },
                React.createElement('div', { style: styles.header },
                    React.createElement('h1', null, '🚀 加密貨幣價格預測系統'),
                    React.createElement('p', null, '使用LSTM模型進行價格預測')
                ),

                React.createElement('div', { style: styles.statusBox },
                    React.createElement('p', null, 
                        React.createElement('strong', null, '狀態: '),
                        message
                    )
                ),

                React.createElement('div', { style: styles.section },
                    React.createElement('h3', null, '📊 系統資訊'),
                    React.createElement('p', null, '可用幣種: ' + (coins.length > 0 ? coins.join(', ') : '載入中...')),
                    React.createElement('p', null, '時間框架: ' + (timeframes.length > 0 ? timeframes.join(', ') : '載入中...'))
                ),

                trainingStatus && React.createElement('div', { style: styles.section },
                    React.createElement('h3', null, '📈 訓練進度'),
                    React.createElement('p', null, '狀態: ' + trainingStatus.status),
                    React.createElement('p', null, '幣種: ' + trainingStatus.coins_completed + '/' + trainingStatus.total_coins),
                    React.createElement('p', null, '時間框架: ' + trainingStatus.timeframes_completed + '/' + trainingStatus.total_timeframes)
                ),

                React.createElement('div', { style: styles.buttonContainer },
                    React.createElement('button',
                        {
                            onClick: this.startTraining,
                            disabled: loading,
                            style: {
                                ...styles.button,
                                opacity: loading ? 0.5 : 1,
                                cursor: loading ? 'not-allowed' : 'pointer'
                            }
                        },
                        loading ? '訓練中...' : '🔧 開始訓練'
                    )
                ),

                React.createElement('div', { style: styles.footer },
                    React.createElement('p', null, '💡 提示: 第一次訓練需要 30-60 分鐘'),
                    React.createElement('p', null, '📖 查看 README.md 了解更多信息')
                )
            )
        );
    }
}

const styles = {
    container: {
        fontFamily: 'Arial, sans-serif',
        maxWidth: '900px',
        margin: '0 auto',
        padding: '20px',
        background: '#f5f5f5',
        minHeight: '100vh'
    },
    header: {
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white',
        padding: '30px',
        borderRadius: '8px',
        textAlign: 'center',
        marginBottom: '20px'
    },
    statusBox: {
        background: 'white',
        padding: '20px',
        borderRadius: '8px',
        marginBottom: '20px',
        border: '2px solid #667eea',
        fontSize: '18px'
    },
    section: {
        background: 'white',
        padding: '20px',
        borderRadius: '8px',
        marginBottom: '20px'
    },
    buttonContainer: {
        textAlign: 'center',
        marginBottom: '20px'
    },
    button: {
        padding: '15px 30px',
        fontSize: '18px',
        background: '#667eea',
        color: 'white',
        border: 'none',
        borderRadius: '6px',
        cursor: 'pointer',
        fontWeight: 'bold',
        transition: 'all 0.3s ease'
    },
    footer: {
        background: 'white',
        padding: '20px',
        borderRadius: '8px',
        textAlign: 'center',
        color: '#666'
    }
};

// 渲染應用
ReactDOM.render(React.createElement(CryptoApp), document.getElementById('root'));
