import load_blackwhite_build6_event_bosses as loader


loader.PREVIEW = loader.ROOT / "black2white2_build6_preview" / "event_bosses_preview.csv"
loader.VERSION_GROUP_ID = 14
loader.LOAD_BUILD = 6
loader.EXPECTED_ROWS = 57
loader.EXPECTED_GAME_ROWS = 4
loader.ALLOWED_GAME_IDS = {"", "21", "22"}


if __name__ == "__main__":
    loader.main()
