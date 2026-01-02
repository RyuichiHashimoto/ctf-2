import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SettingsPanelComponent } from '../components/settings/settings-panel.component';
import { MaxGraphViewComponent } from '../components/contents/maxgraph-view.component';
import { AttackPathService } from '../services/attack-path.service';

@Component({
  selector: 'app-maxgraph-page',
  imports: [CommonModule, SettingsPanelComponent, MaxGraphViewComponent],
  templateUrl: './maxgraph-page.component.html'
})
export class MaxGraphPageComponent implements OnInit {
  constructor(public readonly service: AttackPathService) {}

  ngOnInit(): void {
    this.service.loadAttackScenarios();
    // this.service.connectWebSocket();
  }
}
