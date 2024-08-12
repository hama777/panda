Imports System.Runtime.Intrinsics

Public Class Form1
    Public Const VERSION As String = "1.04"
    Public Const BOROWSER As String = "C:\Program Files\Google\Chrome\Application\chrome.exe"
    Public Const python_exe As String = "D:\AP\python\python.exe"
    '    Public Const homedir As String = "D:\work\tools\panda\"
    Public Const homedir As String = "D:\ols\panda\"
    Public Const resvfile As String = homedir & "resvlist.htm"
    Public Const rentalfile As String = homedir & "rentallist.htm"
    Public Const wishfile As String = homedir & "wishlist.htm"
    Public Const searchfile As String = homedir & "searchres.htm"

    Public apppath As String
    Public opt_d As Boolean
    Public opt_i As Boolean
    Public opt_h As Boolean


    Private Sub cmd_resv_Click(sender As Object, e As EventArgs) Handles cmd_resv.Click
        Dim psInfo As New ProcessStartInfo()
        Dim arg As String
        Dim param As String
        param = ""

        If opt_d = True Then
            param = param & " -d"
        End If
        If opt_i = True Then
            param = param & " -i"
        End If
        If opt_h = True Then
            param = param & " -his"
        End If
        arg = homedir & "resv.py" & param
        cmd_run(arg)

    End Sub

    Private Sub cmd_rental_Click(sender As Object, e As EventArgs) Handles cmd_rental.Click
        Dim psInfo As New ProcessStartInfo()
        Dim arg As String
        Dim param As String
        param = ""

        If opt_d = True Then
            param = param & " -d"
        End If
        arg = homedir & "rental.py" & param
        cmd_run(arg)

    End Sub

    Private Sub cmd_wish_Click(sender As Object, e As EventArgs) Handles cmd_wish.Click
        Dim psInfo As New ProcessStartInfo()
        Dim arg As String
        Dim param As String
        param = ""

        If opt_d = True Then
            param = param & " -d"
        End If
        arg = homedir & "wish.py" & param
        cmd_run(arg)

    End Sub

    Private Sub cmd_search_Click(sender As Object, e As EventArgs) Handles cmd_search.Click
        Dim psInfo As New ProcessStartInfo()
        Dim arg As String
        Dim param As String
        param = ""

        If opt_d = True Then
            param = param & " -d"
        End If
        arg = homedir & "search.py" & param
        cmd_run(arg)

    End Sub
    Private Sub cmd_run(arg As String)
        Dim psInfo As New ProcessStartInfo()
        psInfo.FileName = python_exe  ' 実行するファイル
        psInfo.Arguments = arg
        psInfo.CreateNoWindow = True ' コンソール・ウィンドウを開かない
        psInfo.UseShellExecute = False ' シェル機能を使用しない
        Process.Start(psInfo)

    End Sub

    Private Sub Form1_Load(sender As Object, e As EventArgs) Handles MyBase.Load
        Dim fs_resv As String
        Dim fs_rental As String
        Dim fs_wish As String
        Dim fs_search As String
        apppath = Application.StartupPath() & "\"
        Me.Text = "Panda Menu  " & VERSION
        fs_resv = System.IO.File.GetLastWriteTime(resvfile).ToString("yy/MM/dd(ddd) HH:mm")
        fs_rental = System.IO.File.GetLastWriteTime(rentalfile).ToString("yy/MM/dd(ddd) HH:mm")
        fs_wish = System.IO.File.GetLastWriteTime(wishfile).ToString("yy/MM/dd(ddd) HH:mm")
        fs_search = System.IO.File.GetLastWriteTime(searchfile).ToString("yy/MM/dd(ddd) HH:mm")
        lbl_lastdate.Text = "最終実行日時" & vbCrLf & "予約: " & fs_resv & vbCrLf _
                          & "貸出: " & fs_rental & vbCrLf _
                          & "Wish: " & fs_wish & vbCrLf _
                          & "検索: " & fs_search


    End Sub

    Private Sub ck_display_CheckedChanged(sender As Object, e As EventArgs) Handles ck_display.CheckedChanged
        If ck_display.Checked = True Then
            opt_d = True
        Else
            opt_d = False
        End If

    End Sub

    Private Sub ck_info_CheckedChanged(sender As Object, e As EventArgs) Handles ck_info.CheckedChanged
        If ck_info.Checked = True Then
            opt_i = True
        Else
            opt_i = False
        End If

    End Sub

    Private Sub ck_hist_CheckedChanged(sender As Object, e As EventArgs) Handles ck_hist.CheckedChanged
        If ck_hist.Checked = True Then
            opt_h = True
        Else
            opt_h = False
        End If

    End Sub

    Private Sub cmd_predi_Click(sender As Object, e As EventArgs) Handles cmd_predi.Click
        Dim arg As String

        arg = homedir & "predict.py"
        cmd_run(arg)

    End Sub
End Class
