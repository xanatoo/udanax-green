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
            nativeBuildInputs = [ pkgs.gnumake pkgs.python3 ];

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
              python3 tests/pyxi-protocol.py "$PWD/green/be_source/backend" "$PWD/enfs/sample.enf"
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
              cp pyxi/pyxi pyxi/x88.py pyxi/tktrans.py "$out/share/udanax-green/pyxi/"
              cat > "$out/bin/udanax-pyxi" <<'EOF'
              #!${pkgs.runtimeShell}
              set -eu
              state="''${XDG_STATE_HOME:-$HOME/.local/state}/udanax-green"
              mkdir -p "$state/be"
              if [ ! -e "$state/be/backend" ]; then
                ln -s ${green}/bin/udanax-backend "$state/be/backend"
              fi
              if [ ! -e "$state/be/enf.enf" ]; then
                cp ${green}/share/udanax-green/enfs/sample.enf "$state/be/enf.enf"
              fi
              cd "$state"
              exec ${pythonTk}/bin/python3 "$(dirname "$0")/../share/udanax-green/pyxi/pyxi" "$@"
              EOF
              chmod +x "$out/bin/udanax-pyxi"
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

      apps = forSystems (pkgs: {
        pyxi = {
          type = "app";
          program = "${self.packages.${pkgs.system}.pyxi}/bin/udanax-pyxi";
        };
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
        backend-build = self.packages.${pkgs.system}.default;
        pyxi-build = self.packages.${pkgs.system}.pyxi;
      });
    };
}
