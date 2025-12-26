# ~/.bashrc
# Homebrew shellenv setup
if [ -d "/home/linuxbrew/.linuxbrew" ]; then
  eval "$('/home/linuxbrew/.linuxbrew/bin/brew' shellenv)"
fi

# ...existing bashrc content...
