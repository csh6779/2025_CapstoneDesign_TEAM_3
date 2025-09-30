using NetVips;
using System.IO;
using System.Net.Http.Headers;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;


namespace ATI_IMageTool;

/// <summary>
/// Interaction logic for MainWindow.xaml
/// </summary>
public partial class MainWindow : Window
{
    private static readonly HttpClient _http = new HttpClient();

    public MainWindow()
    {
        InitializeComponent();
        Loaded += async (_, __) =>
        {
            await Web.EnsureCoreWebView2Async();
            Navigate();
        };
    }

    private void Navigate()
    {
        if (ImageIdBox.Text == null) return;

        string id = ImageIdBox.Text.Trim();
        string src = ((ComboBoxItem)SourceBox.SelectedItem!).Content!.ToString()!;
        string url = $"http://localhost:8000/?source={src}&id={id}";
        Web.CoreWebView2.Navigate(url);
    }

    private void OnLoadClick(object sender, RoutedEventArgs e) => Navigate();

    private async void OnUploadToServerClick(object sender, RoutedEventArgs e)
    {
        var ofd = new Microsoft.Win32.OpenFileDialog
        {
            Filter = "Images|*.tif;*.tiff;*.bmp;*.png;*.jpg;*.jpeg",
            Title = "서버에 업로드할 이미지 선택"
        };
        if (ofd.ShowDialog() != true) return;

        string filePath = ofd.FileName;
        string imageId = System.IO.Path.GetFileNameWithoutExtension(filePath);

        try
        {
            using var form = new MultipartFormDataContent();
            using var fs = File.OpenRead(filePath);
            var fileContent = new StreamContent(fs);
            fileContent.Headers.ContentType = new MediaTypeHeaderValue("application/octet-stream");
            form.Add(fileContent, "file", System.IO.Path.GetFileName(filePath));
            form.Add(new StringContent(imageId), "image_id");
            form.Add(new StringContent("true"), "ingest");

            var res = await _http.PostAsync("http://localhost:8000/upload", form);
            res.EnsureSuccessStatusCode();

            using var doc = JsonDocument.Parse(await res.Content.ReadAsStringAsync());
            var id = doc.RootElement.GetProperty("image_id").GetString();
            ImageIdBox.Text = id;
            SourceBox.SelectedIndex = 0; // zarr
            Navigate();
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "업로드 실패");
        }
    }
}
