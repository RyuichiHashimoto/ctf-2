import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AttackPathService } from '../../services/attack-path.service';

@Component({
  selector: 'app-attack-inputs-panel',
  imports: [CommonModule, FormsModule],
  templateUrl: './attack-inputs-panel.component.html'
})
export class AttackInputsPanelComponent {
  constructor(public readonly service: AttackPathService) {}

  onAlgorithmChange(value: string): void {
    this.service.selectedAlgorithm = value;
    this.service.experimentStartNode = '';
    this.service.experimentEndNode = '';
  }

  run(): void {
    void this.service.runExperiment();
  }
}
