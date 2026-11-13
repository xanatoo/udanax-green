{
  description = "Udanax Green (1999) - original Xanadu backend";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems
        (system: f nixpkgs.legacyPackages.${system});
    in {
      packages = forAllSystems (pkgs:
        let
          green = pkgs.stdenv.mkDerivation {
            pname = "udanax-green";
            version = "1999-09-02";
            src = self;
            nativeBuildInputs = [ pkgs.gnumake ];
            # Use the historical build system without editing its sources.
            # Modern GCC defaults to -fno-common; these sources predate it.
            buildPhase = ''
              runHook preBuild
              make -C green/be_source \
                SHELL=${pkgs.bash}/bin/bash \
                CC="$CC" \
                CFLAGS="-O2 -g -std=gnu89 -fcommon -Wno-implicit-function-declaration -Wno-int-conversion" \
                LFLAGS="" \
                all
              runHook postBuild
            '';
            installPhase = ''
              runHook preInstall
              install -Dm755 green/be_source/xumain "$out/bin/udanax-xumain"
              install -Dm755 green/be_source/backend "$out/bin/udanax-backend"
              install -Dm755 green/be_source/backenddaemon "$out/bin/udanax-backenddaemon"
              mkdir -p "$out/share/udanax-green"
              cp -R green/edemo green/olddemo "$out/share/udanax-green/" 2>/dev/null || true
              runHook postInstall
            '';
            meta = with pkgs.lib; {
              description = "Udanax Green hypertext backend";
              homepage = "https://udanax.xanadu.com/green/";
              license = licenses.mit;
              platforms = platforms.linux;
              mainProgram = "udanax-xumain";
            };
          };
        in {
          default = green;
          udanax-green = green;
        });

      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = with pkgs; [ gcc gnumake bash csh gdb python3 tk ];
          shellHook = ''
            echo "Udanax Green development environment"
            echo "Build backend: make -C green/be_source SHELL=$(command -v bash) CFLAGS='-O0 -g -std=gnu89 -fcommon' LFLAGS='''"
            echo "Note: the historical Pyxi frontend requires Python 1.x and has not been ported."
          '';
        };
      });

      checks = forAllSystems (pkgs: {
        backend = self.packages.${pkgs.system}.default;
      });
    };
}
