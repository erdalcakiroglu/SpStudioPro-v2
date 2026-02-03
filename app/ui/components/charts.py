"""
Chart Components - pyqtgraph tabanlı grafik widget'ları

Bu modül Query Stats ve diğer modüller için grafik bileşenlerini içerir:
- SparklineWidget: Mini trend grafikleri (liste görünümü için)
- TrendChartWidget: Detaylı trend grafikleri (detay sayfası için)
- WaitProfileChart: Wait kategorileri için pie/bar chart
"""

from typing import Optional, List, Tuple
from datetime import datetime

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor

import pyqtgraph as pg
import numpy as np

# pyqtgraph global ayarları - Light theme
pg.setConfigOptions(antialias=True, background='#FFFFFF', foreground='#64748B')


class SparklineWidget(QWidget):
    """
    Mini sparkline grafiği
    
    Kullanım alanları:
    - QueryCard'larda trend gösterimi
    - Dashboard kartlarında mini grafikler
    
    Özellikler:
    - Kompakt boyut (varsayılan 80x24 px)
    - Tek çizgi, axis yok
    - Hover'da değer gösterimi yok (performans için)
    """
    
    def __init__(
        self, 
        values: Optional[List[float]] = None,
        color: str = "#0066ff",
        fill_color: Optional[str] = None,
        width: int = 80,
        height: int = 24,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self._values = values or []
        self._color = color
        self._fill_color = fill_color or f"{color}40"  # %25 opacity
        
        self.setFixedSize(width, height)
        self._setup_ui()
        
        if values:
            self.set_values(values)
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # PlotWidget oluştur
        self._plot = pg.PlotWidget()
        self._plot.setBackground('transparent')
        
        # Tüm eksenleri, grid'i ve border'ı kaldır
        self._plot.hideAxis('left')
        self._plot.hideAxis('bottom')
        self._plot.setMenuEnabled(False)
        self._plot.setMouseEnabled(x=False, y=False)
        self._plot.hideButtons()
        
        # ViewBox ayarları
        self._plot.getViewBox().setDefaultPadding(0)
        
        layout.addWidget(self._plot)
    
    def set_values(self, values: List[float]) -> None:
        """Grafik değerlerini ayarla"""
        self._values = values
        self._plot.clear()
        
        if not values or len(values) < 2:
            return
        
        # X ekseni (0'dan başlayarak indeks)
        x = np.arange(len(values))
        y = np.array(values, dtype=float)
        
        # NaN ve inf değerleri temizle
        mask = np.isfinite(y)
        if not mask.any():
            return
        
        # Fill (alan) çiz
        fill_color = QColor(self._fill_color)
        fill_brush = pg.mkBrush(fill_color)
        
        fill_item = pg.FillBetweenItem(
            pg.PlotDataItem(x, y),
            pg.PlotDataItem(x, np.zeros_like(y)),
            brush=fill_brush
        )
        self._plot.addItem(fill_item)
        
        # Çizgi çiz
        pen = pg.mkPen(color=self._color, width=1.5)
        self._plot.plot(x, y, pen=pen)
        
        # Auto range
        self._plot.autoRange()
    
    def set_color(self, color: str, fill_color: Optional[str] = None) -> None:
        """Rengi değiştir"""
        self._color = color
        self._fill_color = fill_color or f"{color}40"
        if self._values:
            self.set_values(self._values)


class TrendChartWidget(QWidget):
    """
    Detaylı trend grafiği
    
    Kullanım alanları:
    - Query Stats detay sayfası
    - Dashboard performans grafikleri
    
    Özellikler:
    - Tam boyutlu grafik
    - X ekseni: Tarih
    - Y ekseni: Değer (duration, cpu, reads vs.)
    - Hover'da tooltip
    - Birden fazla seri desteği
    """
    
    def __init__(
        self, 
        title: str = "",
        y_label: str = "",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self._title = title
        self._y_label = y_label
        self._series: List[Tuple[str, List, List, str]] = []  # (name, x, y, color)
        
        self.setMinimumHeight(200)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # PlotWidget - Light theme
        self._plot = pg.PlotWidget()
        self._plot.setBackground('#FFFFFF')
        
        # Başlık
        if self._title:
            self._plot.setTitle(self._title, color='#0F172A', size='12pt')
        
        # Eksen etiketleri
        self._plot.setLabel('left', self._y_label, color='#64748B')
        self._plot.setLabel('bottom', 'Tarih', color='#64748B')
        
        # Grid
        self._plot.showGrid(x=True, y=True, alpha=0.15)
        
        # Legend
        self._legend = self._plot.addLegend(offset=(10, 10))
        self._legend.setLabelTextColor('#64748B')
        
        # Axis styling - Light theme
        axis_pen = pg.mkPen(color='#E2E8F0')
        self._plot.getAxis('left').setPen(axis_pen)
        self._plot.getAxis('bottom').setPen(axis_pen)
        self._plot.getAxis('left').setTextPen(pg.mkPen(color='#64748B'))
        self._plot.getAxis('bottom').setTextPen(pg.mkPen(color='#64748B'))
        
        layout.addWidget(self._plot)
    
    def clear(self) -> None:
        """Grafiği temizle"""
        self._plot.clear()
        self._series.clear()
        if self._legend:
            self._legend.clear()
    
    def add_series(
        self, 
        name: str, 
        dates: List[datetime], 
        values: List[float],
        color: str = "#0066ff"
    ) -> None:
        """
        Yeni seri ekle
        
        Args:
            name: Seri adı (legend'da gösterilir)
            dates: Tarih listesi
            values: Değer listesi
            color: Çizgi rengi
        """
        if not dates or not values or len(dates) != len(values):
            return
        
        # Tarihleri timestamp'e çevir (pyqtgraph için)
        x = np.array([d.timestamp() if isinstance(d, datetime) else float(i) 
                      for i, d in enumerate(dates)])
        y = np.array(values, dtype=float)
        
        # NaN temizle
        mask = np.isfinite(y)
        x = x[mask]
        y = y[mask]
        
        if len(x) < 2:
            return
        
        # Çizgi ekle
        pen = pg.mkPen(color=color, width=2)
        curve = self._plot.plot(x, y, pen=pen, name=name)
        
        # Noktaları ekle
        scatter = pg.ScatterPlotItem(
            x=x, y=y, 
            size=6, 
            pen=pg.mkPen(color=color), 
            brush=pg.mkBrush(color=color)
        )
        self._plot.addItem(scatter)
        
        self._series.append((name, x.tolist(), y.tolist(), color))
        
        # X ekseni tarih formatı
        axis = self._plot.getAxis('bottom')
        axis.setTicks([[(ts, datetime.fromtimestamp(ts).strftime('%d/%m')) 
                        for ts in x[::max(1, len(x)//5)]]])
    
    def add_duration_series(self, dates: List[datetime], values: List[float]) -> None:
        """Duration serisi ekle (mavi)"""
        self.add_series("Duration (ms)", dates, values, "#0066ff")
    
    def add_cpu_series(self, dates: List[datetime], values: List[float]) -> None:
        """CPU serisi ekle (turuncu)"""
        self.add_series("CPU (ms)", dates, values, "#f97316")
    
    def add_reads_series(self, dates: List[datetime], values: List[float]) -> None:
        """Reads serisi ekle (yeşil)"""
        self.add_series("Logical Reads", dates, values, "#22c55e")


class WaitProfileChart(QWidget):
    """
    Wait profili için horizontal bar chart
    
    Alternatif: Pie chart yerine bar chart kullanıyoruz çünkü:
    - Karşılaştırması daha kolay
    - Küçük yüzdeleri görmek daha kolay
    - Tutarlı UI (WaitProfileBar ile benzer)
    """
    
    def __init__(
        self, 
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self.setMinimumHeight(150)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # PlotWidget - Light theme
        self._plot = pg.PlotWidget()
        self._plot.setBackground('#FFFFFF')
        
        # Eksenleri ayarla
        self._plot.hideAxis('bottom')
        self._plot.showGrid(x=True, y=False, alpha=0.15)
        
        # Sol eksen (kategori adları için)
        self._plot.getAxis('left').setTextPen(pg.mkPen(color='#64748B'))
        
        layout.addWidget(self._plot)
    
    def set_data(
        self, 
        categories: List[str], 
        values: List[float], 
        colors: List[str]
    ) -> None:
        """
        Wait verilerini ayarla
        
        Args:
            categories: Kategori adları
            values: Yüzde değerleri
            colors: Her kategori için renk
        """
        self._plot.clear()
        
        if not categories or not values:
            return
        
        n = len(categories)
        y = np.arange(n)
        x = np.array(values)
        
        # Horizontal bar chart
        for i, (cat, val, color) in enumerate(zip(categories, values, colors)):
            bar = pg.BarGraphItem(
                x0=[0], y=[i], width=[val], height=0.6,
                brush=pg.mkBrush(color=color),
                pen=pg.mkPen(color=color)
            )
            self._plot.addItem(bar)
            
            # Değer etiketi
            text = pg.TextItem(f"{val:.1f}%", color='#0F172A', anchor=(0, 0.5))
            text.setPos(val + 2, i)
            self._plot.addItem(text)
        
        # Y ekseni etiketleri
        ticks = [[(i, cat) for i, cat in enumerate(categories)]]
        self._plot.getAxis('left').setTicks(ticks)
        
        # Range ayarla
        self._plot.setXRange(0, max(values) * 1.2)
        self._plot.setYRange(-0.5, n - 0.5)


class ExecutionTrendChart(QWidget):
    """
    Execution count trend grafiği (bar chart)
    
    Günlük execution sayısını gösterir.
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.setMinimumHeight(150)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Light theme
        self._plot = pg.PlotWidget()
        self._plot.setBackground('#FFFFFF')
        self._plot.setLabel('left', 'Executions', color='#64748B')
        self._plot.showGrid(x=False, y=True, alpha=0.15)
        
        # Axis styling - Light theme
        self._plot.getAxis('left').setTextPen(pg.mkPen(color='#64748B'))
        self._plot.getAxis('bottom').setTextPen(pg.mkPen(color='#64748B'))
        
        layout.addWidget(self._plot)
    
    def set_data(self, dates: List[datetime], executions: List[int]) -> None:
        """
        Execution verilerini ayarla
        
        Args:
            dates: Tarih listesi
            executions: Execution count listesi
        """
        self._plot.clear()
        
        if not dates or not executions:
            return
        
        n = len(dates)
        x = np.arange(n)
        y = np.array(executions, dtype=float)
        
        # Bar chart
        bar = pg.BarGraphItem(
            x=x, height=y, width=0.6,
            brush=pg.mkBrush(color='#6366f1'),
            pen=pg.mkPen(color='#6366f1')
        )
        self._plot.addItem(bar)
        
        # X ekseni tarih etiketleri
        ticks = [[(i, d.strftime('%d/%m') if isinstance(d, datetime) else str(d)) 
                  for i, d in enumerate(dates)]]
        self._plot.getAxis('bottom').setTicks(ticks)
        
        # Range
        self._plot.setXRange(-0.5, n - 0.5)
        self._plot.setYRange(0, max(y) * 1.1)
