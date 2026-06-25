# Gen 2 Trainer Sprites

Place Pokemon Gold/Silver/Crystal trainer battle sprites in this folder.

Use plain `trainer_pool.trainer_pic` values, for example:

```text
TRAINER_PIC_FALKNER
TRAINER_PIC_WHITNEY
TRAINER_PIC_YOUNGSTER
```

For Gen II games, the frontend resolves those to:

```text
/sprites/trainers/gen2/TRAINER_PIC_FALKNER.png
```

Keep the filename stem aligned with Crystal's trainer picture pointers from
`data/trainers/pic_pointers.asm`.
