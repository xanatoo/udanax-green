{
  description = "Udanax Green — the original Xanadu 88.1 C backend";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forSystems = f: nixpkgs.lib.genAttrs systems
        (system: f nixpkgs.legacyPackages.${system});
      # The 1980s code uses K&R C declarations and tentative common symbols.
      legacyCflags = "-O2 -std=gnu89 -fcommon -fno-strict-aliasing "
        + "-Wno-implicit-function-declaration -Wno-int-conversion "
        + "-Wno-return-type";
    in {
      packages = forSystems (pkgs:
        let
          green = pkgs.stdenv.mkDerivation {
            pname = "udanax-green";
            version = "1999-09-29";
            src = self;
            nativeBuildInputs = [ pkgs.gnumake pkgs.python3 pkgs.xorg.xorgserver ];

            buildPhase = ''
              runHook preBuild
              make -C green/be_source -j''${NIX_BUILD_CORES:-1} \
                SHELL=${pkgs.bash}/bin/bash \
                CC="$CC" \
                CFLAGS="${legacyCflags}" \
                LFLAGS="" \
                all
              runHook postBuild
            '';
            doCheck = true;
            checkPhase = ''
              runHook preCheck
              "$CC" ${legacyCflags} -ffunction-sections -fdata-sections \
                tests/freedisk.c -Wl,--gc-sections -o freedisk-test
              ./freedisk-test
              "$CC" ${legacyCflags} -Werror=format-security -Wformat \
                tests/rcfile.c -o rcfile-test
              ./rcfile-test
              sh tests/backend-smoke.sh \
                "$PWD/green/be_source/xumain" "$PWD/enfs/sample.enf"
              sh tests/text-persistence.sh "$PWD/green/be_source/xumain"
              python3 pyxi/test.py > /dev/null
              python3 tests/pyxi-backend-failure.py ${pkgs.coreutils}/bin/false
              sh tests/pyxi-state.sh
              ${pkgs.python3.withPackages (ps: [ ps.tkinter ])}/bin/python3 \
                tests/pyxi-tk-selection.py ${pkgs.xorg.xorgserver}/bin/Xvfb
              python3 tests/pyxi-protocol.py "$PWD/green/be_source/backend" "$PWD/enfs/sample.enf"
              python3 tests/link-persistence.py "$PWD/green/be_source/backend" "$PWD/enfs/sample.enf"
              ${pkgs.python3.withPackages (ps: [ ps.tkinter ])}/bin/python3 \
                tests/pyxi-linked-documents.py "$PWD/green/be_source/backend" \
                "$PWD/enfs/sample.enf" ${pkgs.xorg.xorgserver}/bin/Xvfb
              ${pkgs.python3.withPackages (ps: [ ps.tkinter ])}/bin/python3 \
                tests/pyxi-paste.py "$PWD/green/be_source/backend" \
                "$PWD/enfs/sample.enf" ${pkgs.xorg.xorgserver}/bin/Xvfb
              ${pkgs.python3.withPackages (ps: [ ps.tkinter ])}/bin/python3 \
                tests/pyxi-compare.py "$PWD/green/be_source/backend" \
                "$PWD/enfs/sample.enf" ${pkgs.xorg.xorgserver}/bin/Xvfb
              runHook postCheck
            '';
            installPhase = ''
              runHook preInstall
              install -Dm755 green/be_source/xumain "$out/bin/udanax-xumain"
              install -Dm755 green/be_source/backend "$out/bin/udanax-backend"
              install -Dm755 green/be_source/backenddaemon "$out/bin/udanax-backenddaemon"
              mkdir -p "$out/share/udanax-green" "$out/share/man/man1"
              cp -r green/edemo green/olddemo enfs "$out/share/udanax-green/"
              cp green/man/*.L "$out/share/udanax-green/"
              runHook postInstall
            '';
            meta = with pkgs.lib; {
              description = "Original Udanax Green Xanadu hypertext backend";
              homepage = "https://udanax.xanadu.com/green/";
              license = licenses.mit;
              platforms = platforms.linux;
              mainProgram = "udanax-xumain";
            };
          };
          pythonTk = pkgs.python3.withPackages (ps: [ ps.tkinter ]);
          pyxi = pkgs.stdenvNoCC.mkDerivation {
            pname = "udanax-pyxi";
            version = "1999-09-02-py3";
            src = self;
            dontBuild = true;
            installPhase = ''
              runHook preInstall
              mkdir -p "$out/share/udanax-green/pyxi" "$out/bin"
              cp pyxi/pyxi pyxi/x88.py pyxi/tktrans.py pyxi/docbrowser.py "$out/share/udanax-green/pyxi/"
              install -m755 scripts/prepare-pyxi-state.sh "$out/share/udanax-green/pyxi/prepare-state.sh"
              cat > "$out/bin/udanax-pyxi" <<'EOF'
              #!${pkgs.runtimeShell}
              set -eu
              state="''${UDANAX_GREEN_STATE_DIR:-''${XDG_STATE_HOME:-$HOME/.local/state}/udanax-green}"
              ${pkgs.runtimeShell} "$(dirname "$0")/../share/udanax-green/pyxi/prepare-state.sh" \
                "$state" ${green}/bin/udanax-backend ${green}/share/udanax-green/enfs/sample.enf
              cd "$state"
              exec ${pythonTk}/bin/python3 "$(dirname "$0")/../share/udanax-green/pyxi/pyxi" "$@"
              EOF
              chmod +x "$out/bin/udanax-pyxi"
              cat > "$out/bin/udanax-pyxi-clean" <<'EOF'
              #!${pkgs.runtimeShell}
              set -eu
              export UDANAX_GREEN_STATE_DIR="''${XDG_STATE_HOME:-$HOME/.local/state}/udanax-green-clean"
              exec "$(dirname "$0")/udanax-pyxi" "$@"
              EOF
              chmod +x "$out/bin/udanax-pyxi-clean"
              runHook postInstall
            '';
            meta = with pkgs.lib; {
              description = "Python 3 / Tk frontend for Udanax Green";
              homepage = "https://udanax.xanadu.com/green/";
              license = licenses.mit;
              platforms = platforms.linux;
              mainProgram = "udanax-pyxi";
            };
          };
        in {
          default = green;
          udanax-green = green;
          inherit pyxi;
        });

      apps = forSystems (pkgs:
        let
          green = self.packages.${pkgs.stdenv.hostPlatform.system}.udanax-green;
          pyxi = self.packages.${pkgs.stdenv.hostPlatform.system}.pyxi;
          app = program: description: {
            type = "app";
            inherit program;
            meta = { inherit description; };
          };
        in {
          default = app "${pyxi}/bin/udanax-pyxi"
            "Launch the historical Pyxi hypertext GUI (Python 3 / Tk)";
          pyxi = app "${pyxi}/bin/udanax-pyxi"
            "Run the Pyxi graphical document browser and editor";
          pyxi-clean = app "${pyxi}/bin/udanax-pyxi-clean"
            "Launch Pyxi with a separate clean sample database (leaves existing state untouched)";
          xumain = app "${green}/bin/udanax-xumain"
            "Run the interactive standalone backend protocol console (uses ./enf.enf)";
          backend = app "${green}/bin/udanax-backend"
            "Run the low-level pipe-based backend (requires a protocol client)";
          backenddaemon = app "${green}/bin/udanax-backenddaemon"
            "Run the historical network backend daemon (advanced use)";
        });

      devShells = forSystems (pkgs: {
        default = pkgs.mkShell {
          packages = with pkgs; [ gcc gnumake bash gdb (python3.withPackages (ps: [ ps.tkinter ])) tk ];
          shellHook = ''
            export UDANAX_CFLAGS='${legacyCflags} -g'
            echo 'Udanax Green development environment'
            echo 'Build: make -C green/be_source CC=cc CFLAGS="$UDANAX_CFLAGS" LFLAGS= all'
            echo 'Package: nix build; test flake: nix flake check'
            echo 'GUI: nix run .#pyxi (Python 3 + Tk; state in XDG_STATE_HOME)'
          '';
        };
      });

      checks = forSystems (pkgs: {
        backend-build = self.packages.${pkgs.stdenv.hostPlatform.system}.default;
        pyxi-build = self.packages.${pkgs.stdenv.hostPlatform.system}.pyxi;
      });
    };
}
