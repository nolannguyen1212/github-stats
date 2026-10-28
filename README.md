# github-stats · Matrix Terminal Edition

<img src="assets/header.svg" alt="header" width="100%" />

<p>
<img src="generated/overview.svg" alt="overview" width="49%" />
<img src="generated/languages.svg" alt="languages" width="49%" />
</p>

Repo này generate các SVG phong cách **terminal / Matrix green** cho GitHub
profile bằng GitHub Actions — không cần server, chạy hằng ngày, và đọc được cả
dữ liệu **private repo** nhờ Personal Access Token của chính bạn.

Fork từ [jstrieb/github-stats](https://github.com/jstrieb/github-stats)
(GPL-3.0), đã viết lại template và thêm contribution snake.

## Cấu trúc

| Đường dẫn | Mô tả |
|---|---|
| `templates/overview.svg` | Template card thống kê (stars, forks, contributions, lines changed, views, repos) |
| `templates/languages.svg` | Template card ngôn ngữ — top 6, dạng thanh ASCII `█░` |
| `templates/pinned.svg` | Lưới card cho các repo đang pin trên profile (tối đa 6, tự cập nhật khi đổi pin) |
| `templates/contributions.svg` | Heatmap contribution 1 năm + current/longest streak, best day |
| `generate_images.py` | Điền số liệu vào template → `generated/*.svg` |
| `github_stats.py` | Gọi GitHub GraphQL/REST API để lấy số liệu |
| `assets/header.svg` | Banner terminal có hiệu ứng gõ chữ (tĩnh, tự sửa nội dung) |
| `generated/` | Output do Actions commit: `overview.svg`, `languages.svg`, `pinned.svg`, `contributions.svg`, `snake-dark.svg`, `snake-light.svg` |
| `profile/README.md` | README hoàn chỉnh để copy sang repo profile |
| `.github/workflows/main.yml` | Chạy mỗi ngày 00:05 UTC, khi push lên `master`, hoặc chạy tay |

## Cài đặt

### 1. Tạo Personal Access Token

Workflow cần token riêng (token mặc định của Actions không đọc được dữ liệu
user và private repo).

**Classic token** (đơn giản nhất): *Settings → Developer settings → Personal
access tokens → Tokens (classic) → Generate new token*

- Scopes: `repo` và `read:user`
- Expiration: tuỳ bạn — nhớ gia hạn khi hết hạn, nếu không workflow sẽ fail

> Token mới tạo đôi khi mất vài phút mới hoạt động.

### 2. Thêm secrets vào repo này

*Settings → Secrets and variables → Actions → New repository secret*

| Secret | Bắt buộc | Ví dụ | Ý nghĩa |
|---|---|---|---|
| `ACCESS_TOKEN` | ✅ | `ghp_xxx…` | Token ở bước 1 |
| `EXCLUDED` | | `nolannguyen1212/dotfiles,org/legacy-app` | Repo bỏ qua khi tính thống kê |
| `EXCLUDED_LANGS` | | `HTML,CSS,Jupyter Notebook` | Ngôn ngữ ẩn khỏi card languages |

Forked repo đã được loại trừ sẵn (`EXCLUDE_FORKED_REPOS: true` trong workflow).

> Gợi ý cho profile Go/backend: thêm `HTML,CSS,SCSS,Jupyter Notebook` vào
> `EXCLUDED_LANGS` để card ngôn ngữ không bị lệch bởi file template/notebook.

### 3. Bật quyền ghi cho Actions

*Settings → Actions → General → Workflow permissions →* **Read and write
permissions** → Save. (Workflow đã khai báo `permissions: contents: write`,
nhưng một số tài khoản/org vẫn chặn ở mức repo.)

### 4. Chạy workflow

*Actions → Generate Stats Images → Run workflow*. Sau khoảng 1–3 phút, thư mục
`generated/` sẽ có 4 file SVG mới. Từ đó trở đi workflow tự chạy mỗi ngày.

> Repo này phải **public** — README profile nhúng ảnh qua
> `raw.githubusercontent.com`, URL này không truy cập được nếu repo private.
> Dữ liệu private repo vẫn chỉ xuất hiện dưới dạng con số tổng hợp.

### 5. Tạo profile README

1. Tạo repo **public** tên trùng username: `nolannguyen1212/nolannguyen1212`
   (GitHub sẽ hiện thông báo "special repository").
2. Copy nội dung [`profile/README.md`](profile/README.md) vào `README.md` của
   repo đó.
3. Sửa các chỗ placeholder:
   - email / LinkedIn trong hàng badge đầu trang
   - khối `nolan.yaml` (role, domains, learning…)
   - danh sách badge `~/stack` cho đúng công nghệ bạn dùng

## Tuỳ chỉnh

**Pinned repos** — không cần sửa code: đổi pin trên trang profile GitHub, lần
chạy workflow tiếp theo sẽ vẽ lại `pinned.svg`. Card lấy dữ liệu từ chính danh
sách pin, nên đừng bỏ pin; các ô pin mặc định của GitHub vẫn hiện bên dưới
README và không đổi giao diện được.

**Cài đặt profile nên bật** (Settings → Public profile): *Include private
contributions on my profile* để heatmap đầy đủ hơn; tắt *Show Achievements* để
sidebar gọn hơn.

**Header banner** — sửa text trong `assets/header.svg`. Mỗi dòng được "gõ" ra
bằng cách animate độ rộng của một `clipPath`; nếu dòng lệnh dài hơn, tăng giá
trị `to="520"` tương ứng (~8.4px mỗi ký tự).

**Màu** — palette dùng chung cho mọi file:

| Token | Hex | Dùng cho |
|---|---|---|
| background | `#0a0f0a` | nền card |
| title bar | `#0f1a10` | thanh tiêu đề |
| phosphor | `#00ff41` | prompt, thanh ngôn ngữ, viền |
| mid green | `#00c72c` | key, phần trăm |
| bright text | `#b6ffc6` | giá trị |
| dim | `#1f5f2c` | dấu chấm dẫn, thanh trống |

**Số ngôn ngữ / độ dài thanh** — `MAX_LANGUAGES` và `BAR_WIDTH` ở đầu phần
image generation trong `generate_images.py`.

**Lịch chạy** — sửa `cron` trong `.github/workflows/main.yml`.

## Lưu ý về độ chính xác

- *Lines of code changed* và *views* lấy từ API thống kê của GitHub, có thể
  thiếu ở lần chạy đầu và chính xác dần khi GitHub cache xong (xem
  [jstrieb#2](https://github.com/jstrieb/github-stats/issues/2),
  [#3](https://github.com/jstrieb/github-stats/issues/3),
  [#13](https://github.com/jstrieb/github-stats/issues/13)).
- Views chỉ tính 14 ngày gần nhất và chỉ cho repo bạn có quyền push.
- Nếu `aiohttp` ném exception, log trong tab Actions (public) có thể lộ **tên**
  private repo. Cân nhắc điều này trước khi dùng token có scope `repo`.

## License

GPL-3.0 — xem [LICENSE](LICENSE). Code gốc © Jacob Strieb.
