import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AttackPathService } from '../../services/attack-path.service';
import { LoadGraphPanelComponent } from './load-graph-panel.component';
import { AttackInputsPanelComponent } from './attack-inputs-panel.component';

@Component({
  selector: 'app-settings-panel',
  imports: [CommonModule, LoadGraphPanelComponent, AttackInputsPanelComponent],
  templateUrl: './settings-panel.component.html'
})
export class SettingsPanelComponent {
  constructor(public readonly service: AttackPathService) {}
}
