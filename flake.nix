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
            nativeBuildInputs = [ pkgs.gnumake ];

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
        in { default = green; udanax-green = green; });

      devShells = forSystems (pkgs: {
        default = pkgs.mkShell {
          packages = with pkgs; [ gcc gnumake bash gdb python3 tk ];
          shellHook = ''
            export UDANAX_CFLAGS='${legacyCflags} -g'
            echo 'Udanax Green development environment'
            echo 'Build: make -C green/be_source CC=cc CFLAGS="$UDANAX_CFLAGS" LFLAGS= all'
            echo 'Package: nix build; test flake: nix flake check'
            echo 'The historical Pyxi frontend is not yet ported (Python 1.x).'
          '';
        };
      });

      checks = forSystems (pkgs: {
        backend-build = self.packages.${pkgs.system}.default;
      });
    };
}
