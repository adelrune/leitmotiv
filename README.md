# Leitmotiv

Leitmotiv is a musical pattern manipulation dsl

## Tech Stuff

Leitmotiv is parsed with the lark parser library. It uses music21 as a backend for internal representation of fragments of music and for some format conversion. xml2abc is used to convert from music21 back to abc notation. The music notation images are generated with abcm2ps.

The ltv files are meant to be used in emacs with `iimage-mode`. This handy elisp snippet can be run to evaluate the current file and refresh the inline musical notation :

```elisp
(defun run-leitmotiv ()
  (interactive)
  (progn
    (shell-command (concat
                    "python <PATH_TO>leitmotiv.py "
                    (buffer-file-name)))
    (revert-buffer :ignore-auto :noconfirm)
    (if (not (boundp 'iimage-mode))
        (iimage-mode))
    (iimage-recenter)))
```
