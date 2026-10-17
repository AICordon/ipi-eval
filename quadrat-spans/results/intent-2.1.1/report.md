# AI Cordon Intent 2.1.1 on Quadrat-IPI v1.0.2: the injection's span, 16,800 injected rows

Scored 16,800 of 16,800; version 2.1.1; not judged: 0; flagged without a span: 0. Character level; a row not flagged predicts nothing.

| rows | n | flagged | found | IoU | precision | recall | located, IoU ≥ 0.5 | located, IoU ≥ 0.75 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| all injected | 16,800 | 0.944 | 0.943 | 0.767 | 0.906 | 0.794 | 0.796 | 0.641 |
| flagged only | 15,852 | 1.000 | 0.999 | 0.813 | 0.906 | 0.822 | 0.844 | 0.680 |

By carrier:

| rows | n | flagged | found | IoU | precision | recall | located, IoU ≥ 0.5 | located, IoU ≥ 0.75 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| email | 6,160 | 0.902 | 0.902 | 0.715 | 0.905 | 0.753 | 0.755 | 0.585 |
| doc | 5,920 | 0.978 | 0.977 | 0.805 | 0.903 | 0.835 | 0.836 | 0.683 |
| web | 4,720 | 0.954 | 0.954 | 0.787 | 0.912 | 0.797 | 0.799 | 0.663 |

By injection family:

| rows | n | flagged | found | IoU | precision | recall | located, IoU ≥ 0.5 | located, IoU ≥ 0.75 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| bare | 2,240 | 0.892 | 0.892 | 0.717 | 0.859 | 0.783 | 0.734 | 0.603 |
| execution_surface | 720 | 0.976 | 0.976 | 0.818 | 0.859 | 0.930 | 0.893 | 0.696 |
| forged_frame | 2,240 | 0.976 | 0.976 | 0.763 | 0.893 | 0.762 | 0.770 | 0.619 |
| guard | 720 | 0.931 | 0.931 | 0.743 | 0.928 | 0.752 | 0.754 | 0.621 |
| identity | 2,000 | 0.963 | 0.960 | 0.783 | 0.899 | 0.805 | 0.806 | 0.656 |
| inference | 2,240 | 0.914 | 0.914 | 0.761 | 0.923 | 0.803 | 0.802 | 0.640 |
| output_marking | 1,440 | 0.985 | 0.985 | 0.789 | 0.937 | 0.764 | 0.812 | 0.645 |
| persistence | 2,240 | 0.968 | 0.968 | 0.830 | 0.930 | 0.859 | 0.875 | 0.729 |
| pretext | 720 | 0.842 | 0.842 | 0.687 | 0.916 | 0.734 | 0.750 | 0.574 |
| revocation | 2,240 | 0.950 | 0.949 | 0.752 | 0.903 | 0.766 | 0.777 | 0.611 |

Raising the bar: only rows flagged by the service AND scoring at or above the threshold keep their span; false alarms counted on the 62,999 clean rows of the quadrat-full run of this version (flagged and at or above the threshold).

| score ≥ | flagged | found | located, IoU ≥ 0.5 | located, IoU ≥ 0.75 | false alarms of clean |
|---:|---:|---:|---:|---:|---:|
| 0.970538 | 0.944 | 0.943 | 0.796 | 0.641 | 14 |
| 0.977273 | 0.943 | 0.943 | 0.796 | 0.641 | 14 |
| 0.98913 | 0.941 | 0.940 | 0.794 | 0.640 | 12 |
| 0.995947 | 0.936 | 0.935 | 0.790 | 0.636 | 6 |
| 0.996821 | 0.862 | 0.862 | 0.729 | 0.587 | 3 |
| 0.997168 | 0.779 | 0.779 | 0.658 | 0.531 | 0 |
| 0.997339 | 0.779 | 0.779 | 0.658 | 0.530 | 0 |
| 0.997824 | 0.695 | 0.695 | 0.586 | 0.472 | 0 |
| 0.99807 | 0.695 | 0.694 | 0.586 | 0.472 | 0 |
| 0.998097 | 0.695 | 0.694 | 0.586 | 0.471 | 0 |
| 0.998237 | 0.584 | 0.584 | 0.492 | 0.396 | 0 |
| 0.99929 | 0.584 | 0.584 | 0.491 | 0.396 | 0 |
