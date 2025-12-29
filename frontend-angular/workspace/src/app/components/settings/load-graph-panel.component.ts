import { Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AttackPathService } from '../../services/attack-path.service';

@Component({
  selector: 'app-load-graph-panel',
  imports: [CommonModule, FormsModule],
  templateUrl: './load-graph-panel.component.html'
})
export class LoadGraphPanelComponent implements OnInit {
  @ViewChild('fileInput') fileInput?: ElementRef<HTMLInputElement>;
  selectedFile: File | null = null;
  selectedFileName = '';

  constructor(public readonly service: AttackPathService) {}

  ngOnInit(): void {
    this.service.loadUploadedGraphs();
  }

  handleLoadGraphClick(): void {
    if (this.fileInput?.nativeElement) {
      this.fileInput.nativeElement.value = '';
      this.fileInput.nativeElement.click();
    }
  }

  handleGraphFile(event: Event): void {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    if (file) {
      this.selectedFile = file;
      this.selectedFileName = file.name;
    }
  }

  handleUploadClick(): void {
    if (!this.selectedFile) {
      return;
    }
    this.service.handleGraphFile(this.selectedFile);
  }

  handleUploadSelection(value: string): void {
    this.service.selectedUploadId = value;
    if (value) {
      this.service.loadUploadedGraph(value);
    }
  }

  handleRenderUploadedGraph(): void {
    if (!this.service.selectedUploadId) {
      return;
    }
    this.service.loadUploadedGraph(this.service.selectedUploadId);
  }
}
