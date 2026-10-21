# PR #14 CD-DA playback and CUE pregaps

Source: [kem0x PR #14](https://github.com/mstan/psxrecomp/pull/14), commit
[`0e9df70ca2da6ec67c8e7a1f3e5aaa025fddc369`](https://github.com/mstan/psxrecomp/commit/0e9df70ca2da6ec67c8e7a1f3e5aaa025fddc369).

This branch adapts the reusable Red Book CD-DA stream, Play/GetlocP behavior,
track-end handling, and INDEX 00 pregap model to the newer multi-file CUE reader
on current `origin/master`. It deliberately does not replace that reader with
the older implementation from the source commit.

Excluded from this branch:

- the CD interrupt work from PR #14, already handled independently by PR #20;
- title-specific behavior or addresses;
- the source commit's older multi-file reader implementation, superseded by the
  reader already on master.

Authorship from the source commit is retained in this branch's commit trailer.
