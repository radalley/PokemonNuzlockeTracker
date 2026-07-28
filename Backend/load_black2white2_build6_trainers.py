import load_blackwhite_build6_trainers as loader


loader.PREVIEW_DIR = loader.ROOT / "black2white2_build6_preview"
loader.VERSION_GROUP_ID = 14
loader.LOAD_BUILD = 6
loader.EXPECTED_TRAINERS = 813
loader.EXPECTED_POKEMON = 1808


if __name__ == "__main__":
    loader.main()
