# Gen 1 Trainer Sprites

Place Pokemon Red/Blue/Yellow trainer battle sprites in this folder.

Use plain `trainer_pool.trainer_pic` values, for example:

```text
TRAINER_PIC_YOUNGSTER
TRAINER_PIC_BROCK
TRAINER_PIC_MISTY
```

For Gen I games, the frontend should resolve those to:

```text
/sprites/trainers/gen1/TRAINER_PIC_BROCK.png
```

Keep the filename stem aligned with Red/Blue/Yellow trainer picture pointers from the decomp.
