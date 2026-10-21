{
  description = "Reproducible environment for manim explainer videos (manim, LaTeX, ffmpeg, faster-whisper, pinned model and fonts)";

  # Pinned nixpkgs commit (nixos-unstable, Oct 2026). Bump with: nix flake update
  inputs.nixpkgs.url = "https://github.com/NixOS/nixpkgs/archive/6510408d147d8c5e6d76043e899e9251756f6a75.tar.gz";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAll = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});

      mkEnv = pkgs: rec {
        # Whisper weights pinned to an exact Hugging Face commit, hash-checked.
        modelRev = "3d3d5dee26484f91867d81cb899cfcf72b96be6c";
        hf = name: hash: pkgs.fetchurl {
          url = "https://huggingface.co/Systran/faster-whisper-base.en/resolve/${modelRev}/${name}";
          inherit hash;
        };
        whisperModel = pkgs.linkFarm "faster-whisper-base.en" [
          { name = "config.json";    path = hf "config.json"    "sha256-87w4Ien8dqJ7rlOOEa5bZ33N01K0YAQpznlR05hWmus="; }
          { name = "model.bin";      path = hf "model.bin"      "sha256-KhZpJVOaFgBfFP8yg1n5ua253E+2Mbs7InUmhi6T4u8="; }
          { name = "tokenizer.json"; path = hf "tokenizer.json" "sha256-kpxSUkCUNtzhs4p10au8teEy0XDY4yTk4E7ZFfotIt8="; }
          { name = "vocabulary.txt"; path = hf "vocabulary.txt" "sha256-/3dYh0bTolldMqtbaf/XuVziRBrFdTPLZvw+tXWhFc8="; }
        ];

        # Minimal TeX for manim's MathTex/Tex templates; dvisvgm converts DVI to SVG.
        tex = pkgs.texliveSmall.withPackages (ps: with ps; [
          standalone preview doublestroke relsize everysel ragged2e microtype
          physics setspace rsfs mathastext dvisvgm amsfonts
        ]);

        python = pkgs.python3.withPackages (ps: with ps; [ manim faster-whisper numpy pillow spacy spacy-models.en_core_web_sm ]);

        # Fonts resolved through a private fontconfig, so text renders identically everywhere.
        fontsConf = pkgs.makeFontsConf { fontDirectories = [ pkgs.caladea pkgs.dejavu_fonts ]; };

        tools = [ python tex pkgs.ffmpeg pkgs.coreutils pkgs.bash ];

        envVars = {
          FONTCONFIG_FILE = fontsConf;
          WHISPER_MODEL = whisperModel;
        };

        app = name: script: pkgs.writeShellApplication {
          inherit name;
          runtimeInputs = tools;
          text = ''
            export FONTCONFIG_FILE=${fontsConf}
            export WHISPER_MODEL=${whisperModel}
            ${script} "$@"
          '';
        };
      };
    in {
      devShells = forAll (pkgs:
        let e = mkEnv pkgs; in {
          default = pkgs.mkShell ({
            packages = e.tools;
            shellHook = ''echo "manim explainer env: manim $(python -c 'import manim; print(manim.__version__)')"'';
          } // e.envVars);
          # Optional, large: only for the occasional 3D-rendered signature shot.
          blender = pkgs.mkShell ({
            packages = e.tools ++ [ pkgs.blender ];
          } // e.envVars);
        });

      packages = forAll (pkgs:
        let e = mkEnv pkgs; in {
          whisper-model = e.whisperModel;
          default = pkgs.buildEnv { name = "manim-explainer-env"; paths = e.tools; };
        });

      apps = forAll (pkgs:
        let
          e = mkEnv pkgs;
          mk = name: script: { type = "app"; program = "${e.app name script}/bin/${name}"; };
        in {
          transcribe = mk "transcribe" "python ${self}/scripts/transcribe.py";
          render     = mk "render"     "bash ${self}/scripts/render_all.sh";
          assemble   = mk "assemble"   "python ${self}/scripts/assemble.py";
          grab       = mk "grab"       "python ${self}/scripts/grab.py";
          lint       = mk "lint"       "python ${self}/scripts/lint.py";
        });
    };
}
