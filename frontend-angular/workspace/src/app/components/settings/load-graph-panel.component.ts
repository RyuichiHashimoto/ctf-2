import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AttackPathService } from '../../services/attack-path.service';

@Component({
  selector: 'app-load-graph-panel',
  imports: [CommonModule, FormsModule],
  templateUrl: './load-graph-panel.component.html'
})
export class LoadGraphPanelComponent implements OnInit {
  loadError = '';

  constructor(public readonly service: AttackPathService) {}

  ngOnInit(): void {
    void this.loadList();
  }

  refresh(): void {
    void this.loadList();
  }

  handleUploadSelection(value: string): void {
    this.service.selectedUploadId = value;
    if (value) {
      void this.service.loadUploadedGraph(value);
    } else {
      this.service.graphData$.next(null);
      this.service.predictedPaths$.next([]);
    }
  }

  private async loadList(): Promise<void> {
    this.loadError = '';
    try {
      await this.service.loadUploadedGraphs();
    } catch {
      this.loadError = 'グラフ一覧の取得に失敗しました。バックエンドの接続を確認してください。';
    }
  }
}
