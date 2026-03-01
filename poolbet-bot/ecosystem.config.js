module.exports = {
  apps: [
    {
      name: "poolbet-main",
      script: "python3",
      args: "main.py",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      env: {
        PYTHONUNBUFFERED: "1"
      }
    },
    {
      name: "poolbet-scheduler",
      script: "python3",
      args: "worker_scheduler.py",
      autorestart: true,
      watch: false,
      env: {
        PYTHONUNBUFFERED: "1"
      }
    },
    {
      name: "poolbet-blockchain",
      script: "python3",
      args: "worker_blockchain.py",
      autorestart: true,
      watch: false,
      env: {
        PYTHONUNBUFFERED: "1"
      }
    }
  ]
};
