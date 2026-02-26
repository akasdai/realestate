# To learn more about how to use Nix to configure your environment
# see: https://developers.google.com/idx/guides/customize-idx-env
{ pkgs, ... }: {
  # Which nixpkgs channel to use.
  channel = "stable-23.11"; # or "unstable"
  # Use https://search.nixos.org/packages to find packages
  packages = [
    pkgs.nodejs_20
    pkgs.python3
    pkgs.python312Packages.pip
  ];
  # Sets environment variables in the workspace
  env = {};
  idx = {
    # Search for the extensions you want on https://open-vsx.org/ and use "publisher.id"
    extensions = [
      # "vscodevim.vim"
      "google.gemini-cli-vscode-ide-companion"
    ];
    # Enable previews and customize configuration
    previews = {
      enable = true;
      previews = {
        web = {
          command = ["bash" "-c" "MCP_TRANSPORT=http MCP_PORT=$PORT .venv/bin/python server.py"];
          manager = "web";
        };
      };
    };
    # Workspace lifecycle hooks
    workspace = {
      # Runs when a workspace is first created
      onCreate = {
        # Python 가상환경 생성 및 MCP 서버 의존성 설치
        setup-python-venv = "python3 -m venv .venv && .venv/bin/pip install --upgrade pip && .venv/bin/pip install mcp httpx python-dotenv";
        # Open editors for the following files by default, if they exist:
        default.openFiles = [ "server.py" "_helpers.py" ];
      };
      # Runs when the workspace is (re)started
      onStart = {
        # 가상환경이 없으면 재설치
        ensure-venv = "[ -d .venv ] || (python3 -m venv .venv && .venv/bin/pip install mcp httpx python-dotenv)";
        # MCP 서버 HTTP 모드로 자동 시작
        start-mcp-server = "MCP_TRANSPORT=http .venv/bin/python server.py &";
      };
    };
  };
}